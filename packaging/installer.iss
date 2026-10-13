; CosmoLights - Script de instalador (Inno Setup 6)
; Compilar:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
; Requiere haber generado antes dist\CosmoLights\ con PyInstaller.

#define MyAppName "CosmoLights"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CosmoLights"
#define MyAppExeName "CosmoLights.exe"

[Setup]
AppId={{7D3C2A51-6B8E-4F1C-9A0E-C05A1F1E9B42}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\installer
OutputBaseFilename=CosmoLights-Setup-{#MyAppVersion}
SetupIconFile=..\src\ui\assets\CosmoLightLogoIcon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "Iniciar CosmoLights con Windows (minimizado en la bandeja)"; GroupDescription: "Opciones:"; Flags: unchecked

[Files]
Source: "..\dist\CosmoLights\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"
