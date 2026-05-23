; NSIS-скрипт установщика AppMonitor
; Для компиляции: makensis installer.nsi

Unicode True
RequestExecutionLevel admin

!define PRODUCT_NAME "AppMonitor"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "AppMonitor"
!define PRODUCT_WEB_SITE ""
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\AppMonitor.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; MUI — Modern User Interface
!include "MUI2.nsh"

; Иконка установщика
!define MUI_ICON "app_icon.ico"
!define MUI_UNICON "app_icon.ico"

; Страницы
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Язык
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

; Путь к собранному EXE
!define EXE_SOURCE "dist\AppMonitor.exe"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "AppMonitor_Setup_${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Section "Установка AppMonitor" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite ifnewer

    ; Копируем основной EXE
    File "${EXE_SOURCE}"

    ; Создаём папки для данных и логов
    CreateDirectory "$INSTDIR\data"
    CreateDirectory "$INSTDIR\logs"

    ; Ярлык в меню Пуск
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\AppMonitor.exe" "" "$INSTDIR\AppMonitor.exe" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Удалить ${PRODUCT_NAME}.lnk" "$INSTDIR\uninst.exe" "" "$INSTDIR\uninst.exe" 0

    ; Ярлык на рабочем столе
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\AppMonitor.exe" "" "$INSTDIR\AppMonitor.exe" 0

    ; Запись в реестр для деинсталляции
    WriteUninstaller "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\AppMonitor.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\AppMonitor.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoRepair" 1

    ; Добавляем в автозагрузку при установке
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AppMonitor" '"$INSTDIR\AppMonitor.exe"'

    ; Разрешаем порт 8765 в брандмауэре Windows
    SimpleFC::AddApplication "AppMonitor API" "$INSTDIR\AppMonitor.exe" 0 2 "" 1
    Pop $0

SectionEnd

Section -Post
    ; Запускаем приложение после установки
    ExecShell "" "$INSTDIR\AppMonitor.exe"
SectionEnd

; Деинсталляция
Section Uninstall
    ; Удаляем из автозагрузки
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AppMonitor"

    ; Удаляем ярлыки
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"

    ; Удаляем файлы
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\logs"
    Delete "$INSTDIR\AppMonitor.exe"
    Delete "$INSTDIR\uninst.exe"
    RMDir "$INSTDIR"

    ; Удаляем из реестра
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
    DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
SectionEnd
