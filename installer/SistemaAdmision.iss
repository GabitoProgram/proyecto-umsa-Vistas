#define MyAppName "Sistema de Admisión UMSA"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "UMSA"
#define MyAppExeName "SistemaAdmision.exe"

[Setup]
AppId={{8E13F4F4-4B6D-4D0A-9B9E-20261027A001}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SistemaAdmision
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=SistemaAdmision-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Files]
Source: "..\dist\SistemaAdmision\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\drivers\ZKFingerSDK_Windows_Standard_setup.exe"; DestDir: "{app}\drivers"; Flags: ignoreversion
Source: "..\config\app_config.example.json"; DestDir: "{app}\config"; DestName: "app_config.json"; Flags: onlyifdoesntexist

[Dirs]
Name: "{app}\config"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\drivers\ZKFingerSDK_Windows_Standard_setup.exe"; Description: "Instalar driver del lector ZKTeco (opcional)"; Flags: postinstall skipifsilent unchecked
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent
