"""
Interactive Trip & Task Planning Engine for NIVA.
Handles conversational slot collection across multi-turn interactions,
gathers missing requirements (destination, travelers count, budget, duration),
generates detailed day-by-day itineraries with budget breakdowns, and writes
the completed plan directly into a formatted document on the user's Desktop.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NIVA.TripPlanner")

WORD_TO_NUMBER = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "a": 1, "an": 1, "couple": 2, "single": 1, "solo": 1
}


class TripPlanner:
    """Manages multi-turn trip planning and itinerary generation."""

    @staticmethod
    def is_trip_planning_request(text: str) -> bool:
        """Determines if the utterance is requesting a trip or vacation plan."""
        t = text.lower().strip()
        trip_patterns = [
            r"\bplan\s+(?:a\s+|my\s+|our\s+)?(?:trip|vacation|holiday|tour|itinerary|journey|travel)\b",
            r"\b(?:help\s+me\s+plan|organize|create|prepare)\s+(?:a\s+|my\s+|our\s+)?(?:trip|vacation|holiday|tour|itinerary)\b",
            r"\b(?:trip|vacation|holiday|tour|itinerary)\s+(?:planning|plan)\b",
            r"\bplan\s+for\s+(?:\d+|seven|five|three|four|two|ten)\s+days?\b",
            r"\bgoing\s+on\s+a\s+trip\b",
        ]
        for pat in trip_patterns:
            if re.search(pat, t, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def extract_trip_slots(text: str) -> Dict[str, Any]:
        """Extracts trip planning parameters from an utterance."""
        t = text.lower().strip()
        slots: Dict[str, Any] = {}

        # 1. Duration extraction (e.g. "seven days", "7 days", "a week", "3 days", "weekend")
        m_week = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|a|an)?\s*weeks?\b", t)
        if m_week:
            count_w = m_week.group(1) or "1"
            val = WORD_TO_NUMBER.get(count_w, int(count_w) if count_w.isdigit() else 1)
            days = val * 7
            slots["duration"] = f"{days} days"
            slots["duration_days"] = days
        else:
            m_day = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen)\s*(?:days?|nights?)\b", t)
            if m_day:
                count_d = m_day.group(1)
                val = WORD_TO_NUMBER.get(count_d, int(count_d) if count_d.isdigit() else 7)
                slots["duration"] = f"{val} days"
                slots["duration_days"] = val
            elif "weekend" in t:
                slots["duration"] = "2 days"
                slots["duration_days"] = 2

        # 2. Destination extraction
        # Ignore duration phrases like "for seven days", "for 5 days", "for a week"
        clean_for_dest = re.sub(r"\bfor\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+(?:days?|weeks?|nights?)\b", "", text, flags=re.IGNORECASE)
        dest_m = re.search(r"\b(?:to|in|visit|destination\s+is|going\s+to)\s+([a-zA-Z\s]{2,25}?)(?:\s+(?:for|with|with\s+a|and|on|by|at|budget)|\b|$)", clean_for_dest, re.IGNORECASE)
        if dest_m:
            dest_candidate = dest_m.group(1).strip()
            # Filter out non-destination words
            non_dest = ["a trip", "my trip", "the trip", "vacation", "holiday", "fun", "me", "us", "people", "persons", "days", "a week", "seven", "five", "three", "four", "two", "one"]
            if dest_candidate.lower() not in non_dest and not re.search(r"\b(?:day|week|night|person|people)\b", dest_candidate.lower()):
                slots["destination"] = dest_candidate.title()
        else:
            # Check for known destinations or single place names
            known_places = [
                "goa", "manali", "paris", "dubai", "kerala", "ooty", "jaipur", "agra", "delhi", "mumbai",
                "shimla", "kashmir", "ladakh", "singapore", "maldives", "bali", "tokyo", "london", "rome",
                "switzerland", "bangkok", "phuket", "vizag", "hyderabad", "tirupati", "pondicherry", "munnar",
                "coorg", "darjeeling", "varanasi", "rishikesh", "amritsar", "udaipur", "andaman"
            ]
            for p in known_places:
                if re.search(rf"\b{p}\b", t):
                    slots["destination"] = p.title()
                    break

        # 3. Number of people / travelers
        m_ppl = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:people|persons|travelers|friends|adults|members|guys)\b", t)
        if m_ppl:
            count_p = m_ppl.group(1)
            val = WORD_TO_NUMBER.get(count_p, int(count_p) if count_p.isdigit() else 2)
            slots["people"] = val
        elif "me and my friend" in t or "2 of us" in t or "two of us" in t:
            slots["people"] = 2
        elif "solo" in t or "alone" in t or "just me" in t or "myself" in t:
            slots["people"] = 1
        elif "family" in t:
            m_fam = re.search(r"family\s+of\s+(\d+|one|two|three|four|five|six)", t)
            if m_fam:
                c = m_fam.group(1)
                slots["people"] = WORD_TO_NUMBER.get(c, int(c) if c.isdigit() else 4)
            else:
                slots["people"] = 4

        # 4. Budget extraction
        # Look for numbers >= 500 or numbers associated with budget/rupees/k/lakh
        b_patterns = [
            r"\b(?:budget\s+(?:is|of)?\s*|under\s+|around\s+|approx\s+)?(?:rs\.?|inr|\$)?\s*(\d{1,3}(?:,\d{3})+|\d+)\s*(k|lakh|lakhs|thousand)?\s*(?:rupees|inr|budget|dollars|bucks)\b",
            r"\b(?:budget\s+(?:is|of)?\s*)(?:rs\.?|inr|\$)?\s*(\d{1,3}(?:,\d{3})+|\d+)\s*(k|lakh|lakhs|thousand)?\b",
            r"\b(\d{4,9})\b",  # Any 4-9 digit standalone number (e.g. 50000, 25000)
        ]
        for pat in b_patterns:
            bm = re.search(pat, t)
            if bm:
                raw_num = bm.group(1).replace(",", "")
                mult = bm.group(2) if len(bm.groups()) >= 2 and bm.group(2) else None
                if raw_num.isdigit():
                    val = int(raw_num)
                    # Don't confuse with duration or people count
                    if val in [slots.get("duration_days"), slots.get("people")]:
                        continue
                    if mult == "k":
                        val *= 1000
                    elif mult in ["lakh", "lakhs"]:
                        val *= 100000
                    elif mult == "thousand":
                        val *= 1000
                    slots["budget"] = f"{val:,} INR"
                    slots["budget_amount"] = val
                    break

        return slots

    @staticmethod
    def get_missing_requirements(session: Dict[str, Any]) -> List[str]:
        """Returns list of essential requirements still missing from session."""
        missing = []
        if not session.get("destination"):
            missing.append("destination")
        if not session.get("people"):
            missing.append("how many people are going")
        if not session.get("budget"):
            missing.append("what is your approximate budget")
        if not session.get("duration"):
            missing.append("how many days the trip will be")
        return missing

    @staticmethod
    def format_clarification_question(session: Dict[str, Any], missing: List[str]) -> str:
        """Constructs natural conversational question asking for the exact missing details."""
        duration_str = session.get("duration", "your trip")
        dest = session.get("destination")
        ppl = session.get("people")

        if dest and not ppl and not session.get("budget"):
            return f"Great, {dest} for {duration_str}! How many people will be traveling, and what is your approximate budget?"
        elif dest and ppl and not session.get("budget"):
            return f"Almost ready for {dest} with {ppl} travelers for {duration_str}! What is your approximate budget for the trip?"
        elif not dest and ppl and session.get("budget"):
            return f"Planning a {duration_str} trip for {ppl} people with a budget of {session['budget']}! What destination do you have in mind?"
        else:
            # All or most missing
            parts = []
            if "destination" in missing:
                parts.append("what is the destination")
            if "how many people are going" in missing:
                parts.append("how many people are going")
            if "what is your approximate budget" in missing:
                parts.append("what is your approximate budget")

            if len(parts) == 3:
                return f"I'd love to help you plan your {duration_str}! To create the best itinerary for you, could you tell me: {parts[0]}, {parts[1]}, and {parts[2]}?"
            elif len(parts) == 2:
                return f"To customize your {duration_str} itinerary, could you tell me: {parts[0]} and {parts[1]}?"
            elif len(parts) == 1:
                return f"Just one detail needed for your {duration_str}: {parts[0]}?"
            return f"Where would you like to travel, how many people are going, and what is your approximate budget?"

    @classmethod
    def update_session(cls, session: Dict[str, Any], user_input: str) -> Tuple[Dict[str, Any], List[str]]:
        """Updates the existing planning session with slots extracted from follow-up user input."""
        new_slots = cls.extract_trip_slots(user_input)

        # Direct answer heuristics for short turns:
        # e.g., if user just says "Goa" or "Paris" and destination is missing
        clean_input = user_input.strip().rstrip(".?!")
        if "destination" not in new_slots and not session.get("destination"):
            if len(clean_input.split()) <= 3 and not re.search(r"\d", clean_input) and clean_input.lower() not in ["yes", "no", "ok", "sure", "cancel"]:
                new_slots["destination"] = clean_input.title()

        # If user just specifies a number like "4" or "4 people" and people is missing
        if "people" not in new_slots and not session.get("people"):
            m_single_num = re.match(r"^(\d+|one|two|three|four|five|six|seven|eight)\s*(?:people|persons|of\s+us)?$", clean_input.lower())
            if m_single_num:
                v = m_single_num.group(1)
                new_slots["people"] = WORD_TO_NUMBER.get(v, int(v) if v.isdigit() else 2)

        # If user just specifies budget like "50k" or "50000"
        if "budget" not in new_slots and not session.get("budget"):
            m_single_b = re.match(r"^(?:rs\.?|inr|\$)?\s*(\d+)(k|lakh|thousand)?\s*(?:rupees|inr|bucks)?$", clean_input.lower())
            if m_single_b:
                val = int(m_single_b.group(1))
                mult = m_single_b.group(2)
                if mult == "k":
                    val *= 1000
                elif mult == "lakh":
                    val *= 100000
                new_slots["budget"] = f"{val:,} INR"
                new_slots["budget_amount"] = val

        session.update(new_slots)
        missing = cls.get_missing_requirements(session)
        return session, missing

    @classmethod
    def generate_itinerary(cls, session: Dict[str, Any]) -> Dict[str, Any]:
        """Generates comprehensive day-by-day travel plan and itemized budget."""
        dest = session.get("destination", "Your Destination")
        days = session.get("duration_days", 7)
        ppl = session.get("people", 2)
        budget = session.get("budget", "Flexible Budget")
        budget_amt = session.get("budget_amount", 50000)

        # Budget Allocation Calculations
        hotel_budget = int(budget_amt * 0.40)
        food_budget = int(budget_amt * 0.30)
        activity_budget = int(budget_amt * 0.20)
        transport_budget = int(budget_amt * 0.10)

        # Generate Day-by-Day schedule tailored to destination
        dest_lower = dest.lower()
        daily_plans = []

        if "goa" in dest_lower:
            templates = [
                ("Day 1: Arrival & Sunset Chill", "Arrive in Goa, check into hotel/resort. Relax after journey, head to Calangute or Baga beach for a scenic sunset, and enjoy fresh seafood at a beachside shack."),
                ("Day 2: North Goa Heritage & Forts", "Visit historical Fort Aguada and lighthouse with panoramic Arabian Sea views. Explore Chapora Fort (Dil Chahta Hai point) and Vagator beach. Enjoy the evening night market or beach café."),
                ("Day 3: Water Sports & Coastal Adventure", "Thrilling water sports morning at Anjuna or Calangute: parasailing, jet-skiing, and banana boat rides. Afternoon relaxation at Morjim beach. Sunset dinner cruise on the Mandovi river."),
                ("Day 4: Old Goa & Latin Quarter Heritage", "Discover Old Goa UNESCO heritage churches: Basilica of Bom Jesus and Se Cathedral. Afternoon walking tour of Fontainhas (Latin Quarter in Panjim) admiring Portuguese architecture and colorful streets."),
                ("Day 5: South Goa Serenity & Scenic Beaches", "Travel to peaceful South Goa. Visit Colva and Benaulim beaches. Experience a scenic sunset at Palolem beach or butterfly beach boat ride. Enjoy tranquil beachside dinner."),
                ("Day 6: Dudhsagar Waterfalls & Spice Plantation", "Full-day excursion to majestic Dudhsagar Waterfalls. Guided tour through a lush Sahyadri Spice Plantation including a traditional Goan buffet lunch and elephant bathing."),
                ("Day 7: Souvenir Shopping & Farewell Departure", "Morning souvenir shopping at Panaji municipal market for cashew nuts, feni, and handicrafts. Relaxing beachside brunch, checkout, and transfer to airport/station for departure.")
            ]
        elif "manali" in dest_lower or "himachal" in dest_lower:
            templates = [
                ("Day 1: Arrival & Old Manali Vibe", "Arrival in Manali, mountain resort check-in. Evening stroll through Old Manali cafés, Hadimba Devi Temple, and Mall Road."),
                ("Day 2: Solang Valley Snow & Adventure", "Full day at Solang Valley: paragliding, zorbing, and cable car ropeway. Stunning views of snow-capped Himalayan peaks."),
                ("Day 3: Atal Tunnel & Sissu (Lahaul Valley)", "Scenic drive through the engineering marvel Atal Tunnel into pristine Lahaul Valley. Visit Sissu waterfall and riverside trails."),
                ("Day 4: Rohtang Pass High Altitude Excursion", "High-altitude mountain pass journey to Rohtang Pass (3,978m). Snow activities, breathtaking vistas, and mountain photography."),
                ("Day 5: Naggar Castle & Art Gallery", "Cultural day visiting historical Naggar Castle, Nicholas Roerich Art Gallery, and peaceful apple orchards overlooking the Beas river."),
                ("Day 6: Vashisht Hot Springs & Jogini Falls Trek", "Morning trek through pine forests to Jogini Waterfalls. Therapeutic dip in Vashisht natural sulfur hot springs. Evening café hopping."),
                ("Day 7: Shopping & Departure", "Shop for Himachali woolen shawls, wooden craftwork, and fresh jams on Mall Road. Departure with unforgettable mountain memories.")
            ]
        else:
            templates = [
                (f"Day 1: Welcome to {dest}", f"Arrival in {dest}, hotel check-in and acclimation. Evening orientation stroll around city center and authentic local welcome dinner."),
                (f"Day 2: Iconic Landmarks & Sightseeing", f"Guided exploration of {dest}'s most famous historical monuments, museums, and panoramic viewpoints."),
                (f"Day 3: Outdoor Adventures & Nature", f"Exciting day trip into surrounding nature, parks, or scenic coastal/mountain attractions with outdoor activities."),
                (f"Day 4: Cultural Immersion & Local Markets", f"Immerse in local traditions: visit bustling artisan bazaars, historic quarters, and sample regional street delicacies."),
                (f"Day 5: Hidden Gems & Scenic Day Trip", f"Venture slightly off the beaten path to peaceful villages, viewpoints, and unique cultural attractions nearby."),
                (f"Day 6: Leisure, Relaxation & Farewell Feast", f"Relaxed morning for personal exploration, photography, and luxury dining. Festive farewell evening dinner."),
                (f"Day 7: Souvenir Shopping & Departure", f"Morning souvenir shopping for specialty local goods, packing up, and safe transit back home.")
            ]

        # Slice or repeat to match requested days
        for i in range(days):
            t_idx = i % len(templates)
            day_num = i + 1
            title = f"Day {day_num}: {templates[t_idx][0].split(': ')[-1]}"
            desc = templates[t_idx][1]
            daily_plans.append({"day": day_num, "title": title, "description": desc})

        spoken_msg = (
            f"I have created a complete {days}-day itinerary for {dest} for {ppl} people within your {budget} budget! "
            f"It features daily sightseeing, adventure activities, local cuisine, and an itemized budget breakdown. "
            f"I have also saved and opened the full itinerary document on your Desktop."
        )

        return {
            "destination": dest,
            "duration": f"{days} days",
            "duration_days": days,
            "people": ppl,
            "budget": budget,
            "budget_breakdown": {
                "Accommodation / Stays": f"{hotel_budget:,} INR (~{int(hotel_budget/days):,} / night)",
                "Food & Dining": f"{food_budget:,} INR (~{int(food_budget/days):,} / day)",
                "Activities & Entry Tickets": f"{activity_budget:,} INR",
                "Local Transport & Fuel": f"{transport_budget:,} INR",
                "Total Estimated Cost": f"{budget_amt:,} INR"
            },
            "daily_plans": daily_plans,
            "travel_tips": [
                f"Carry valid government photo IDs for all {ppl} travelers.",
                "Book activity tickets and vehicle rentals in advance for peak season discounts.",
                "Keep cash handy for beach shacks, entry fees, and local markets.",
                "Stay hydrated and carry sunscreen, power banks, and comfortable walking shoes."
            ],
            "spoken_summary": spoken_msg
        }

    @classmethod
    def save_and_open_itinerary_document(cls, itinerary: Dict[str, Any]) -> str:
        """Writes formatted itinerary document to Desktop and opens it for the user."""
        dest_clean = re.sub(r"[^\w\s-]", "", itinerary["destination"]).strip().replace(" ", "_")
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop_dir, f"Trip_Itinerary_{dest_clean}.txt")

        # Format complete document text
        content = []
        content.append("=" * 70)
        content.append(f"  {itinerary['duration_days']}-DAY TRIP ITINERARY: {itinerary['destination'].upper()}")
        content.append("=" * 70)
        content.append(f"Destination:  {itinerary['destination']}")
        content.append(f"Duration:     {itinerary['duration']}")
        content.append(f"Travelers:    {itinerary['people']} Person(s)")
        content.append(f"Total Budget: {itinerary['budget']}")
        content.append("-" * 70)
        content.append("ESTIMATED BUDGET BREAKDOWN:")
        for category, amount in itinerary["budget_breakdown"].items():
            content.append(f"  • {category:<30}: {amount}")
        content.append("-" * 70)
        content.append("DAY-BY-DAY ITINERARY SCHEDULE:")
        content.append("-" * 70)

        for p in itinerary["daily_plans"]:
            content.append(f"\n[{p['title']}]")
            content.append(f"  {p['description']}\n")

        content.append("-" * 70)
        content.append("ESSENTIAL TRAVEL & PACKING TIPS:")
        for tip in itinerary["travel_tips"]:
            content.append(f"  ✓ {tip}")
        content.append("=" * 70)
        content.append("Generated by NIVA Autonomous Windows AI Assistant")
        content.append("=" * 70)

        full_text = "\n".join(content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        logger.info(f"Saved trip itinerary to: {file_path}")

        # Open the generated file so the user sees it immediately on screen
        try:
            import subprocess
            subprocess.Popen(["notepad.exe", file_path])
        except Exception as e:
            logger.warning(f"Could not open Notepad for itinerary: {e}")

        return file_path
