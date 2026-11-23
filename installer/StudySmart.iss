; © 2026 Miguel Ángel Martínez. Todos los derechos reservados.
; Instalador de StudySmart (Inno Setup 6). Se compila con build.ps1:  ISCC /DAppVersion=1.2.3 installer\StudySmart.iss
; Instala por usuario (sin permisos de administrador) para que las actualizaciones sean silenciosas.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "StudySmart"
#define Repo "https://github.com/OpTicXit/StudySmart"

[Setup]
AppId={{8F3C2A71-5B4E-4D9A-9C61-2E7A4F0B9D13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Miguel Ángel Martínez
AppCopyright=© 2026 Miguel Ángel Martínez. Todos los derechos reservados.
AppPublisherURL={#Repo}
AppSupportURL={#Repo}/issues
AppUpdatesURL={#Repo}/releases
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=StudySmart-Setup-{#AppVersion}
SetupIconFile=studysmart.ico
UninstallDisplayIcon={app}\StudySmart.exe
UninstallDisplayName={#AppName}
LicenseFile=..\build\LICENSE.txt
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoCopyright=© 2026 Miguel Ángel Martínez

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; quita archivos de la versión anterior antes de copiar la nueva
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\StudySmart\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\StudySmart.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\StudySmart.exe"; Tasks: desktopicon

[Run]
; también corre en las actualizaciones silenciosas: vuelve a abrir StudySmart al terminar
Filename: "{app}\StudySmart.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall
