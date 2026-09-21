#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "JARVIS"
#define MyAppPublisher "JARVIS Project"
#define MyAppExeName "JARVIS.exe"

[Setup]
AppId={{B0A91370-83F9-4A83-89EE-0D5D5D00A551}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\JARVIS
DefaultGroupName=JARVIS
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=JARVIS-Setup-{#MyAppVersion}
SetupIconFile=..\assets\jarvis.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
ChangesAssociations=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Start JARVIS automatically when I sign in"; GroupDescription: "Startup:"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\release\JARVIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\JARVIS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\JARVIS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\JARVIS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start JARVIS"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
