; Inno Setup Script for Drama Reels
; Creates a Windows installer with desktop shortcut

#define MyAppName "Drama Reels"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Archanist"
#define MyAppURL "https://github.com/uzunaruto/drama-reels"
#define MyAppExeName "DramaReels.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer-output
OutputBaseFilename=DramaReels-Setup-{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "indonesian"; MessagesFile: "compiler:Languages\Indonesian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start Drama Reels when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Main executable
Source: "dist\DramaReels.exe"; DestDir: "{app}"; Flags: ignoreversion

; Tools (ffmpeg, yt-dlp)
Source: "tools\ffmpeg.exe"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
Source: "tools\yt-dlp.exe"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist

; License
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
Name: "{userappdata}\DramaReels"
Name: "{userappdata}\DramaReels\downloads"
Name: "{userappdata}\DramaReels\clips"
Name: "{userappdata}\DramaReels\subtitles"
Name: "{userappdata}\DramaReels\jobs"
Name: "{userappdata}\DramaReels\logs"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Open Drama Reels"; Filename: "http://localhost:7860"
Name: "{group}\Data Folder"; Filename: "{userappdata}\DramaReels"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Auto-start with Windows
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DramaReels"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Drama Reels now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\DramaReels"

[Code]
// Check if app is already running
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Try to check if port 7860 is in use
  if Exec('cmd.exe', '/c netstat -an | findstr :7860', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      if MsgBox('Drama Reels might already be running on port 7860.' + #13#10 +
                'Continue anyway?', mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
    end;
  end;
end;
