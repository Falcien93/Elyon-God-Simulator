<#
.SYNOPSIS
    Package a playable Windows demo of the Elyon UE 5.8 project.

.DESCRIPTION
    Calls RunUAT BuildCookRun for Win64 in Shipping or Development, cooks the
    given maps, archives the staged build, zips it, and writes a log.
    Continuous integration does not install Unreal. Pass -DryRun to print the
    RunUAT arguments without starting the engine.

.PARAMETER EngineRoot
    Unreal Engine 5.8 install. Default: C:\Program Files\Epic Games\UE_5.8

.PARAMETER Project
    ElyonUE project file. Default: C:\ElyonSlice\ElyonUE.uproject

.PARAMETER Configuration
    Shipping or Development. Default: Shipping.

.PARAMETER Maps
    Unreal map paths to cook, joined with '+' for RunUAT -map.
    Default: /Game/Maps/Day1_Garden

.PARAMETER ArchiveRoot
    Parent folder for the archived build, the zip, and the log.
    Default: C:\ElyonSlice\Packaged

.PARAMETER ZipPath
    Destination zip. Default: ArchiveRoot\ElyonUE-Win64-<Configuration>.zip

.PARAMETER LogPath
    Summary log. Default: ArchiveRoot\package_demo-<Configuration>.log

.PARAMETER DryRun
    Validate arguments, write the log and the RunUAT command, and do not
    start RunUAT or zip a build.
#>
[CmdletBinding()]
param(
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8',
    [string]$Project = 'C:\ElyonSlice\ElyonUE.uproject',
    [ValidateSet('Shipping', 'Development')]
    [string]$Configuration = 'Shipping',
    [string[]]$Maps = @('/Game/Maps/Day1_Garden'),
    [string]$ArchiveRoot = 'C:\ElyonSlice\Packaged',
    [string]$ZipPath = '',
    [string]$LogPath = '',
    [switch]$DryRun
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$script:DemoLogPath = $null

function Join-PackagePath {
    param(
        [Parameter(Mandatory = $true)][string]$Parent,
        [Parameter(Mandatory = $true)][string]$Child
    )
    # Windows paths stay strings. Join-Path would look up a PSDrive named C,
    # which a dry run on another operating system does not have.
    $base = $Parent.TrimEnd('\', '/')
    $leaf = $Child.TrimStart('\', '/')
    if ($base -match '^[A-Za-z]:' -or $base.Contains('\')) {
        $base = ($base -replace '/', '\').TrimEnd('\')
        $leaf = ($leaf -replace '/', '\').TrimStart('\')
        return ($base + '\' + $leaf)
    }
    return (Join-Path -Path $base -ChildPath $leaf)
}

function Write-DemoLog {
    param([Parameter(Mandatory = $true)][string]$Message)
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    if ($script:DemoLogPath) {
        Add-Content -LiteralPath $script:DemoLogPath -Value $line -Encoding utf8
    }
    Write-Host $line
}

function Test-ShellSafe {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if ($Value -match '["&|<>^%()]') {
        throw "$Label contains a character the packager will not pass to RunUAT."
    }
}

function Assert-DemoArguments {
    param(
        [Parameter(Mandatory = $true)][string]$Engine,
        [Parameter(Mandatory = $true)][string]$ProjectPath,
        [Parameter(Mandatory = $true)][string]$ClientConfig,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$MapList,
        [Parameter(Mandatory = $true)][string]$ArchiveParent
    )

    if ([string]::IsNullOrWhiteSpace($Engine)) {
        throw 'EngineRoot is required.'
    }
    Test-ShellSafe -Value $Engine -Label 'EngineRoot'
    if ([string]::IsNullOrWhiteSpace($ProjectPath) -or -not $ProjectPath.ToLowerInvariant().EndsWith('.uproject')) {
        throw "Project must be a .uproject path. Got: $ProjectPath"
    }
    Test-ShellSafe -Value $ProjectPath -Label 'Project'
    if ($ClientConfig -ne 'Shipping' -and $ClientConfig -ne 'Development') {
        throw 'Configuration must be Shipping or Development.'
    }
    if ([string]::IsNullOrWhiteSpace($ArchiveParent)) {
        throw 'ArchiveRoot is required.'
    }
    Test-ShellSafe -Value $ArchiveParent -Label 'ArchiveRoot'
    if ($null -eq $MapList -or @($MapList).Count -lt 1) {
        throw 'At least one map is required.'
    }
    foreach ($map in @($MapList)) {
        if ($map -notmatch '^/Game/[A-Za-z0-9_./-]+$') {
            throw "Map is not a /Game/ asset path: $map"
        }
        if ($map.Contains('+')) {
            throw "Map path cannot contain '+': $map"
        }
        Test-ShellSafe -Value $map -Label 'Map'
    }
}

function Get-RunUatArguments {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectPath,
        [Parameter(Mandatory = $true)][string]$ClientConfig,
        [AllowEmptyCollection()]
        [string[]]$MapList,
        [Parameter(Mandatory = $true)][string]$ArchiveDirectory
    )

    Assert-DemoArguments -Engine $EngineRoot -ProjectPath $ProjectPath -ClientConfig $ClientConfig -MapList $MapList -ArchiveParent $ArchiveRoot
    $joinedMaps = @($MapList) -join '+'
    # BEGIN UAT ARGS
    return @(
        'BuildCookRun',
        "-project=$ProjectPath",
        '-noP4',
        '-platform=Win64',
        "-clientconfig=$ClientConfig",
        '-build',
        '-cook',
        '-stage',
        '-pak',
        '-archive',
        "-archivedirectory=$ArchiveDirectory",
        "-map=$joinedMaps",
        '-prereqs',
        '-compressed',
        '-unattended',
        '-utf8output'
    )
    # END UAT ARGS
}

function Format-CmdArgument {
    param([Parameter(Mandatory = $true)][string]$Argument)
    if ($Argument -match '[\s"]') {
        return '"' + ($Argument -replace '"', '\"') + '"'
    }
    return $Argument
}

function Invoke-RunUat {
    param(
        [Parameter(Mandatory = $true)][string]$RunUatBat,
        [Parameter(Mandatory = $true)][string[]]$UatArguments,
        [Parameter(Mandatory = $true)][string]$ProjectPath,
        [switch]$SkipLaunch
    )

    $commandParts = @($RunUatBat) + @($UatArguments)
    $commandLine = ($commandParts | ForEach-Object { Format-CmdArgument -Argument $_ }) -join ' '
    Write-DemoLog "RunUAT command: $commandLine"
    Write-DemoLog ('UAT_ARGV=' + (@($UatArguments) -join '|'))
    if ($SkipLaunch) {
        Write-DemoLog 'Dry run: RunUAT was not started.'
        return 0
    }
    if (-not (Test-Path -LiteralPath $RunUatBat -PathType Leaf)) {
        throw "RunUAT.bat was not found at $RunUatBat"
    }
    if (-not (Test-Path -LiteralPath $ProjectPath -PathType Leaf)) {
        throw "Project was not found at $ProjectPath"
    }

    $uatTranscript = [System.IO.Path]::ChangeExtension($script:DemoLogPath, '.uat.log')
    if (Test-Path -LiteralPath $uatTranscript) {
        Remove-Item -LiteralPath $uatTranscript -Force
    }
    Set-Content -LiteralPath $uatTranscript -Value '' -Encoding utf8
    Write-DemoLog "RunUAT transcript: $uatTranscript"

    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = 'cmd.exe'
    $processInfo.Arguments = '/d /s /c "' + $commandLine + ' 2>&1"'
    $processInfo.WorkingDirectory = Split-Path -Parent $ProjectPath
    $processInfo.UseShellExecute = $false
    $processInfo.RedirectStandardOutput = $true
    $processInfo.StandardOutputEncoding = New-Object System.Text.UTF8Encoding $false
    $processInfo.CreateNoWindow = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo
    [void]$process.Start()
    while ($null -ne ($uatLine = $process.StandardOutput.ReadLine())) {
        Add-Content -LiteralPath $uatTranscript -Value $uatLine -Encoding utf8
        Write-Host $uatLine
    }
    $process.WaitForExit()
    $code = $process.ExitCode
    if ($null -eq $code) {
        $code = 1
    }
    Write-DemoLog "RunUAT exit code $code"
    return [int]$code
}

function Find-StagedPlatform {
    param([Parameter(Mandatory = $true)][string]$ArchiveDirectory)
    foreach ($name in @('Windows', 'WindowsNoEditor', 'WindowsClient')) {
        $candidate = Join-PackagePath -Parent $ArchiveDirectory -Child $name
        if (Test-Path -LiteralPath $candidate -PathType Container) {
            return $candidate
        }
    }
    return $null
}

function Compress-StagedBuild {
    param(
        [Parameter(Mandatory = $true)][string]$PlatformDir,
        [Parameter(Mandatory = $true)][string]$DestinationZip,
        [Parameter(Mandatory = $true)][string]$ProjectPath
    )

    $gameName = [System.IO.Path]::GetFileNameWithoutExtension($ProjectPath)
    $exe = Get-ChildItem -LiteralPath $PlatformDir -Filter ($gameName + '.exe') -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $exe) {
        throw "Packaged build has no $gameName.exe under $PlatformDir."
    }
    Write-DemoLog "Playable executable: $($exe.FullName)"

    if (Test-Path -LiteralPath $DestinationZip) {
        Remove-Item -LiteralPath $DestinationZip -Force
    }
    $parent = Split-Path -Parent $PlatformDir
    $leaf = Split-Path -Leaf $PlatformDir
    $tar = Get-Command -Name 'tar.exe' -ErrorAction SilentlyContinue
    if ($tar) {
        & tar.exe -a -cf $DestinationZip -C $parent $leaf
        if ($LASTEXITCODE -ne 0) {
            throw "tar.exe could not zip $PlatformDir (exit $LASTEXITCODE)."
        }
    }
    else {
        Compress-Archive -Path $PlatformDir -DestinationPath $DestinationZip -CompressionLevel Optimal
    }
    if (-not (Test-Path -LiteralPath $DestinationZip -PathType Leaf)) {
        throw "Zip was not written to $DestinationZip"
    }
    return $DestinationZip
}

if ([string]::IsNullOrWhiteSpace($ZipPath)) {
    $ZipPath = Join-PackagePath -Parent $ArchiveRoot -Child ('ElyonUE-Win64-{0}.zip' -f $Configuration)
}
if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Join-PackagePath -Parent $ArchiveRoot -Child ('package_demo-{0}.log' -f $Configuration)
}
Test-ShellSafe -Value $ZipPath -Label 'ZipPath'
Test-ShellSafe -Value $LogPath -Label 'LogPath'

$logDirectory = Split-Path -Parent $LogPath
if ($logDirectory) {
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
}
$zipDirectory = Split-Path -Parent $ZipPath
if ($zipDirectory) {
    New-Item -ItemType Directory -Force -Path $zipDirectory | Out-Null
}
$script:DemoLogPath = $LogPath
Set-Content -LiteralPath $script:DemoLogPath -Value 'ElyonUE Windows demo package' -Encoding utf8

try {
    $archiveDirectory = Join-PackagePath -Parent $ArchiveRoot -Child $Configuration
    $runUat = Join-PackagePath -Parent $EngineRoot -Child 'Engine\Build\BatchFiles\RunUAT.bat'
    Write-DemoLog "EngineRoot=$EngineRoot"
    Write-DemoLog "Project=$Project"
    Write-DemoLog "Configuration=$Configuration"
    Write-DemoLog ('Maps=' + (@($Maps) -join ','))
    Write-DemoLog "ArchiveDirectory=$archiveDirectory"
    Write-DemoLog "ZipPath=$ZipPath"

    $uatArguments = @(Get-RunUatArguments -ProjectPath $Project -ClientConfig $Configuration -MapList $Maps -ArchiveDirectory $archiveDirectory)
    $exitCode = Invoke-RunUat -RunUatBat $runUat -UatArguments $uatArguments -ProjectPath $Project -SkipLaunch:$DryRun
    if ($DryRun) {
        Write-DemoLog 'Dry run finished. No build was cooked and no zip was written.'
        exit 0
    }
    if ($exitCode -ne 0) {
        Write-DemoLog "ERROR: RunUAT failed with exit code $exitCode"
        exit $exitCode
    }

    $platformDir = Find-StagedPlatform -ArchiveDirectory $archiveDirectory
    if (-not $platformDir) {
        throw "No Win64 archive (Windows, WindowsNoEditor, or WindowsClient) under $archiveDirectory"
    }
    Write-DemoLog "Staged platform: $platformDir"
    $writtenZip = Compress-StagedBuild -PlatformDir $platformDir -DestinationZip $ZipPath -ProjectPath $Project
    Write-DemoLog "Zip written: $writtenZip"
    exit 0
}
catch {
    Write-DemoLog ("ERROR: " + $_.Exception.Message)
    exit 1
}
