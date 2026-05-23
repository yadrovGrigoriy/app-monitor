"""
Скрипт для обновления installer.nsi с поддержкой тихой установки.
Запускать: python scripts/update_installer_nsi.py
"""
import os

content = """\
; AppMonitor Installer - NSIS script
; Сборка установщика для Windows, ставит AppMonitor в Program Files

Unicode true
RequestExecutionLevel admin

; --- Параметры -------------------------------------------------------
!define PRODUCT_NAME "AppMonitor"
!define PRODUCT_VERSION "1.1.0"
!define PRODUCT_PUBLISHER "AppMonitor Team"
!define PRODUCT_WEB_SITE "https://appmonitor.local"
!define PRODUCT_DIR "$PROGRAMFILES64\\${PRODUCT_NAME}"
!define PRODUCT_UNINSTALL_KEY "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${PRODUCT_NAME}"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\\dist\\AppMonitor_Setup_${PRODUCT_VERSION}.exe"
InstallDir "${PRODUCT_DIR}"
InstallDirRegKey HKLM "${PRODUCT_UNINSTALL_KEY}" "InstallDir"
ShowInstDetails show
ShowUnInstDetails show

; --- MUI (Modern UI) -------------------------------------------------
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; Страницы установки
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\\installer\\LICENSE_ANSI.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Страницы удаления
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Языки
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

; --- Основные файлы --------------------------------------------------

Section "!Основные файлы" SecCore
    SectionIn RO

    SetOutPath "$INSTDIR"

    File "..\\dist\\AppMonitor.exe"
    File /nonfatal "..\\data\\cert.pem"
    File /nonfatal "..\\data\\key.pem"
    File "..\\LICENSE.txt"

    WriteUninstaller "$INSTDIR\\Uninstall.exe"

    WriteRegStr HKLM "${PRODUCT_UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "${PRODUCT_UNINSTALL_KEY}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "${PRODUCT_UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "${PRODUCT_UNINSTALL_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr HKLM "${PRODUCT_UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\\AppMonitor.exe"
    WriteRegDWORD HKLM "${PRODUCT_UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD HKLM "${PRODUCT_UNINSTALL_KEY}" "NoRepair" 1

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${PRODUCT_UNINSTALL_KEY}" "EstimatedSize" "$0"
SectionEnd

Section "Ярлык в меню Пуск" SecStartMenu
    CreateDirectory "$SMPROGRAMS\\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\AppMonitor.lnk" \\
        "$INSTDIR\\AppMonitor.exe" "" "$INSTDIR\\AppMonitor.exe" 0
    CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\Удалить AppMonitor.lnk" \\
        "$INSTDIR\\Uninstall.exe" "" "$INSTDIR\\Uninstall.exe" 0
SectionEnd

Section "Ярлык на рабочем столе" SecDesktop
    CreateShortCut "$DESKTOP\\AppMonitor.lnk" \\
        "$INSTDIR\\AppMonitor.exe" "" "$INSTDIR\\AppMonitor.exe" 0
SectionEnd

Section "Автозагрузка (рекомендуется)" SecAutostart
    WriteRegStr HKCU \\
        "Software\\Microsoft\\Windows\\CurrentVersion\\Run" \\
        "AppMonitor" \\
        "$INSTDIR\\AppMonitor.exe"
SectionEnd

; --- Описания компонентов --------------------------------------------
LangString DESC_SecCore ${LANG_RUSSIAN} "Основные файлы приложения (обязательно)"
LangString DESC_SecCore ${LANG_ENGLISH} "Core program files (required)"
LangString DESC_SecStartMenu ${LANG_RUSSIAN} "Добавить ярлыки в меню Пуск"
LangString DESC_SecStartMenu ${LANG_ENGLISH} "Add shortcuts to Start Menu"
LangString DESC_SecDesktop ${LANG_RUSSIAN} "Добавить ярлык на рабочий стол"
LangString DESC_SecDesktop ${LANG_ENGLISH} "Add shortcut to Desktop"
LangString DESC_SecAutostart ${LANG_RUSSIAN} "Автоматически запускать AppMonitor при входе в Windows"
LangString DESC_SecAutostart ${LANG_ENGLISH} "Automatically start AppMonitor on Windows login"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} $(DESC_SecCore)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} $(DESC_SecStartMenu)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SecDesktop)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecAutostart} $(DESC_SecAutostart)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; --- Удаление --------------------------------------------------------
Section "Uninstall"
    ExecWait 'taskkill /f /im AppMonitor.exe'

    DeleteRegValue HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" "AppMonitor"
    RMDir /r "$SMPROGRAMS\\${PRODUCT_NAME}"
    Delete "$DESKTOP\\AppMonitor.lnk"
    RMDir /r "$INSTDIR"
    DeleteRegKey HKLM "${PRODUCT_UNINSTALL_KEY}"

    IfFileExists "$APPDATA\\AppMonitor\\*.*" 0 +3
        MessageBox MB_YESNO|MB_ICONQUESTION \\
            "Удалить папку с настройками ($APPDATA\\AppMonitor)?$\\n$\\nВнимание: будут удалены все ваши данные!" \\
            IDNO +2
        RMDir /r "$APPDATA\\AppMonitor"
SectionEnd
"""

nsis_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'installer', 'installer.nsi')
with open(nsis_path, 'w', encoding='cp1251') as f:
    f.write(content)
print(f'OK: {nsis_path}')
