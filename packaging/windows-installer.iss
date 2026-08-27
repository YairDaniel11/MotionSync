; Inno Setup script for MotionSync (Windows installer)
; AppVersion is injected from the CI workflow via /DAppVersion=x.y.z

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

[Setup]
AppId={{7A6E1B42-9C3D-4F8A-B1D2-52E8F0A9C771}
AppName=MotionSync
AppVersion={#AppVersion}
AppPublisher=YairDaniel11
DefaultDirName={autopf}\MotionSync
DefaultGroupName=MotionSync
DisableProgramGroupPage=yes
; Relative to this .iss file, so the installer lands in dist\Output (what CI uploads).
OutputDir=..\dist\Output
OutputBaseFilename=MotionSync-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\MotionSync.exe

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start MotionSync automatically with Windows"; Flags: unchecked

[Files]
Source: "..\dist\MotionSync.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MotionSync"; Filename: "{app}\MotionSync.exe"
Name: "{group}\Uninstall MotionSync"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MotionSync"; Filename: "{app}\MotionSync.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "MotionSync"; ValueData: """{app}\MotionSync.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\MotionSync.exe"; Description: "{cm:LaunchProgram,MotionSync}"; Flags: nowait postinstall skipifsilent
