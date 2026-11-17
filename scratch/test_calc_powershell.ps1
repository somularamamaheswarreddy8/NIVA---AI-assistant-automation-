Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$nameCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, "Calculator")
$calc = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $nameCond)

if (-not $calc) {
    Write-Host "CALCULATOR_NOT_FOUND"
    exit 1
}

Write-Host "FOUND_CALCULATOR: $($calc.Current.Name) (ProcessId: $($calc.Current.ProcessId))"

# Find CalculatorResults
$resCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, "CalculatorResults")
$display = $calc.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $resCond)

if ($display) {
    Write-Host "DISPLAY_TEXT: $($display.Current.Name)"
} else {
    Write-Host "DISPLAY_NOT_FOUND"
}
