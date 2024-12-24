<#
.Synopsis
Makefile script in PowerShell that contains commands useful during development for Red.

.Description
Available commands:
   reformat                   Reformat all .py files being tracked by git.
   stylecheck                 Check which tracked .py files need reformatting.
   stylediff                  Show the post-reformat diff of the tracked .py files
                              without modifying them.
   newenv                     Create or replace this project's virtual environment.
   syncenv                    Sync this project's virtual environment to Red's latest
                              dependencies.
   activateenv                Activates project's virtual environment.

.Parameter Command
Command to execute. See Cmdlet's description for more information.

#>

# I'm too dumb for PowerShell, so $script:availableCommands needs to be defined in 2 places // Jack

[CmdletBinding()]
param (
    [Parameter(Mandatory=$false)]
    [ArgumentCompleter({
        param (
            $commandName,
            $parameterName,
            $wordToComplete,
            $commandAst,
            $fakeBoundParameters
        )
        $script:availableCommands = @("reformat", "stylecheck", "stylediff", "newenv", "syncenv", "activateenv")
        return $script:availableCommands | Where-Object { $_ -like "$wordToComplete*" }
    })]
    [String]
    $command,
    [switch]
    $help = $false
)

function reformat() {
    & $script:venvPython -m black $PSScriptRoot
}

function stylecheck() {
    & $script:venvPython -m black --check $PSScriptRoot
    Exit $LASTEXITCODE
}

function stylediff() {
    & $script:venvPython -m black --check --diff $PSScriptRoot
    Exit $LASTEXITCODE
}

function newenv() {
    py -3.8 -m venv --clear .venv
    & $PSScriptRoot\.venv\Scripts\python.exe -m pip install -U pip wheel
    syncenv
}

function syncenv() {
    & $PSScriptRoot\.venv\Scripts\python.exe -m pip install -Ur .\tools\dev-requirements.txt
}

function activateenv() {
    & $PSScriptRoot\.venv\Scripts\Activate.ps1
}

$script:availableCommands = @("reformat", "stylecheck", "stylediff", "newenv", "syncenv", "activateenv")

if (Test-Path -LiteralPath "$PSScriptRoot\.venv" -PathType Container) {
    $script:venvPython = "$PSScriptRoot\.venv\Scripts\python.exe"
} else {
    $script:venvPython = "python"
}

if ($help -or !$command) {
    Get-Help $MyInvocation.InvocationName
    exit
}

switch ($command) {
    {$script:availableCommands -contains $_} {
        & $command
        break
    }
    default {
        Write-Host (
            """$command"" is not a valid command.",
            "To see available commands, type: ""$($MyInvocation.InvocationName) -help"""
        )
        break
    }
}

