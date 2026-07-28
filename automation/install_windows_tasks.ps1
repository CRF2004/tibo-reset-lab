$ErrorActionPreference = "Stop"

$distro = "Ubuntu"
$project = "/mnt/c/users/12879/desktop/projects/tibo"
$preflight = "wsl.exe -d $distro --cd $project python3 scripts/task8_daily_run.py --phase preflight"
$forecast = "wsl.exe -d $distro --cd $project python3 scripts/task8_daily_run.py --phase forecast"
$score = "wsl.exe -d $distro --cd $project python3 scripts/task8_daily_run.py --phase score"

# Windows host timezone is Asia/Shanghai: 00:50 and 01:00 local correspond to
# 16:50 and 17:00 UTC on the previous UTC calendar date.
schtasks.exe /Create /F /SC DAILY /ST 00:50 /TN "TiboResearchPreflight" /TR $preflight
schtasks.exe /Create /F /SC DAILY /ST 01:00 /TN "TiboResearchForecast" /TR $forecast
schtasks.exe /Create /F /SC DAILY /ST 01:10 /TN "TiboResearchScore" /TR $score

schtasks.exe /Query /FO LIST /TN "TiboResearchPreflight"
schtasks.exe /Query /FO LIST /TN "TiboResearchForecast"
schtasks.exe /Query /FO LIST /TN "TiboResearchScore"
