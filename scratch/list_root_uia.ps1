Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
Write-Host "Total children of root: $($all.Count)"
foreach ($el in $all) {
    if ($el.Current.Name) {
        Write-Host "Name: '$($el.Current.Name)' | Class: '$($el.Current.ClassName)' | PID: $($el.Current.ProcessId)"
    }
}
