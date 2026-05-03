; Inno Setup script for Majestic Translator.
; Compile with:  ISCC.exe installer\installer.iss
; Or via the build.ps1 wrapper, which detects ISCC automatically.

#define MyAppName       "Majestic Translator"
#define MyAppShortName  "MajesticTranslator"
#define MyAppVersion    "0.1.0"
#define MyAppPublisher  "Majestic Translator contributors"
#define MyAppURL        "https://github.com/your-user/majestic-translator"
#define MyAppExeName    "MajesticTranslator.exe"

[Setup]
AppId={{8A6F2F0E-2E4A-4B3F-9F0D-7C6F2E1A0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppShortName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=output
OutputBaseFilename={#MyAppShortName}-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "polish";  MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Pull in the entire PyInstaller --onedir output. Run build.ps1 first.
Source: "..\dist\MajesticTranslator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Don't leave the user-specific config behind on uninstall.
Type: filesandordirs; Name: "{app}\config.json"
