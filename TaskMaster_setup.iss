; Inno Setup Installer Script for TaskMaster (Single EXE)
; تنصيب برنامج TaskMaster

#define AppName "TaskMaster"
#define AppVersion "1.0.0"
#define AppPublisher "TaskMaster"
#define AppExeName "TaskMaster.exe"
#define AppMutex "TaskMasterAppMutex"

[Setup]
; Basic settings
AppId={{A1B2C3D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; File settings
OutputDir=installer_output
OutputBaseFilename=TaskMaster_Setup_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
; Interface
WizardStyle=modern
PrivilegesRequired=admin
CreateAppDir=yes
DisableDirPage=no
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
; Appearance
BackColor=clBtnFace
BackColor2=clBlack
BackColorDirection=top_to_bottom
FlatComponentsList=no
ShowTasksTreeLines=yes
; Language
ShowLanguageDialog=yes

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Single EXE file
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
; Run app after install
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Cleanup database files on uninstall
Type: filesandordirs; Name: "{userappdata}\TaskMaster"

[Code]
function IsAppRunning(const FileName: string): Boolean;
var
    FWM: HANDLE;
begin
    Result := False;
    FWM := CreateMutex(nil, True, PChar('{#AppMutex}'));
    if (FWM <> 0) and (GetLastError = ERROR_ALREADY_EXISTS) then
        Result := True;
end;

function InitializeSetup(): Boolean;
begin
    if IsAppRunning('{#AppExeName}') then
    begin
        MsgBox(ExpandConstant('{cm:SetupAppRunningError}'), mbError, MB_OK);
        Result := False;
    end
    else
        Result := True;
end;

function InitializeUninstall(): Boolean;
begin
    if IsAppRunning('{#AppExeName}') then
    begin
        if MsgBox('The program is currently running. Close it and continue?', 'البرنامج يعمل حالياً. إغلاقه ومتابعة؟',
                  mbConfirmation, MB_YESNO) = IDYES then
            Result := True
        else
            Result := False;
    end
    else
        Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
    if CurStep = ssPostInstall then
    begin
        CreateDir(ExpandConstant('{userappdata}\TaskMaster'));
    end;
end;

[CustomMessages]
arabic.CreateDesktopIcon=إنشاء أيقونة على سطح المكتب
arabic.CreateQuickLaunchIcon=إنشاء أيقونة تشغيل سريع
arabic.AdditionalIcons=أيقونات إضافية
arabic.LaunchProgram=تشغيل برنامج TaskMaster
arabic.SetupAppRunningError=برنامج TaskMaster يعمل حالياً. يرجى إغلاقه أولاً

english.CreateDesktopIcon=Create a desktop icon
english.CreateQuickLaunchIcon=Create a quick launch icon
english.AdditionalIcons=Additional icons
english.LaunchProgram=Launch TaskMaster
english.SetupAppRunningError=TaskMaster is currently running. Please close it first
