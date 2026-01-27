# Fixed Increment-Version function to replace the broken one

function Increment-Version {
  param(
    [string]$Version,
    [switch]$Major,
    [switch]$Minor,
    [switch]$Patch
  )

  # Parse version string - use DIFFERENT variable names to avoid PowerShell case-insensitive conflict
  $verParts = $Version.Split('.')
  $verMajor = [int]$verParts[0]
  $verMinor = [int]$verParts[1]
  $verPatchNum = [int]$verParts[2]

  # Increment based on switch parameter
  if ($Major) {
    $verMajor++
    $verMinor = 0
    $verPatchNum = 0
  } elseif ($Minor) {
    $verMinor++
    $verPatchNum = 0
  } elseif ($Patch) {
    $verPatchNum++
  } else {
    # Default: increment patch
    $verPatchNum++
  }

  return "$verMajor.$verMinor.$verPatchNum"
}
