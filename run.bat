@echo off
setlocal enabledelayedexpansion

title NIVA - Universal AI Computer Control System
color 0B

cd /d "%~dp0\jarvis"
call run.bat %*
