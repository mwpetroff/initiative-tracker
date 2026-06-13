"""
Initiative Tracker — Excel export with VBA macro module.
Generates a styled .xlsx workbook + a .bas module file users import into Excel.
Works on Mac and Windows — no binary OLE2 generation.
"""
import os, psycopg2, xlsxwriter
from datetime import datetime

# ─── DB ───────────────────────────────────────────────────────────────────────
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur  = conn.cursor()

cur.execute("""
    SELECT id, title, description, status, progress, priority,
           owner, department, start_date, end_date, created_at, updated_at
    FROM initiatives
    ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
             CASE status WHEN 'delayed' THEN 1 WHEN 'at_risk' THEN 2
                         WHEN 'on_track' THEN 3 ELSE 4 END, title
""")
initiatives = cur.fetchall()

cur.execute("""
    SELECT u.id, i.id, i.title, u.note, u.author, u.created_at
    FROM initiative_updates u
    JOIN initiatives i ON i.id = u.initiative_id
    ORDER BY u.created_at DESC
""")
updates = cur.fetchall()

cur.execute("""
    SELECT department,
           COUNT(*),
           SUM(CASE WHEN status='on_track'  THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='at_risk'   THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='delayed'   THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),
           ROUND(AVG(progress),1)
    FROM initiatives WHERE department IS NOT NULL
    GROUP BY department ORDER BY 2 DESC
""")
by_dept = cur.fetchall()

cur.execute("""
    SELECT COUNT(*),
           SUM(CASE WHEN status='on_track'    THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='at_risk'     THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='delayed'     THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='completed'   THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='not_started' THEN 1 ELSE 0 END),
           ROUND(AVG(progress),1)
    FROM initiatives
""")
summary = cur.fetchone()
cur.close(); conn.close()

NOW = datetime.now().strftime("%B %d, %Y")

# ─── VBA SOURCE CODE (Windows + Mac compatible) ──────────────────────────────
VBA_CODE = r'''Attribute VB_Name = "InitiativeTracker"
Option Explicit

' ==============================================================================
'  Initiative Tracker VBA — CRUD via REST API
'  Works on: Windows Excel 2016+ and Mac Excel 2016+
'
'  Windows : MSXML2.XMLHTTP60 (built-in COM)
'  Mac     : curl via MacScript/AppleScript (curl is pre-installed on macOS)
'  JSON    : pure-VBA parser — no COM / no VBScript.RegExp — works on both
'
'  SETUP
'    1. Enable macros when prompted (or: File > Options > Trust Center >
'       Macro Settings > Enable all macros)
'    2. Set your API URL in the Config sheet cell B4
'    3. Run TestConnection to verify, then run CreateButtons once to set up
'       the sidebar buttons and the two built-in form sheets
'
'  USAGE
'    Sidebar buttons on the Initiatives sheet open styled form sheets.
'    Fill in the form and click Save — the sheet updates immediately.
'    No multi-step dialog chains needed.
' ==============================================================================

' ─── Config ───────────────────────────────────────────────────────────────────
Private Function ApiBase() As String
    On Error Resume Next
    ApiBase = Trim(ThisWorkbook.Sheets("Config").Range("B4").Value)
    If ApiBase = "" Then ApiBase = "http://localhost/api"
    On Error GoTo 0
End Function

' ─── HTTP — platform switch ───────────────────────────────────────────────────
Private Function Http(method As String, path As String, _
                      Optional body As String = "") As String
#If Mac Then
    Http = HttpMac(method, ApiBase() & path, body)
#Else
    Http = HttpWin(method, ApiBase() & path, body)
#End If
End Function

' Windows: MSXML2.XMLHTTP60
#If Not Mac Then
Private Function HttpWin(method As String, url As String, body As String) As String
    Dim x As Object
    Set x = CreateObject("MSXML2.XMLHTTP60")
    x.Open method, url, False
    x.setRequestHeader "Content-Type", "application/json"
    x.setRequestHeader "Accept", "application/json"
    If body <> "" Then x.Send body Else x.Send
    If x.Status >= 200 And x.Status < 300 Then
        HttpWin = x.responseText
    Else
        Err.Raise vbObjectError + 500, , "HTTP " & x.Status & Chr(10) & x.responseText
    End If
End Function
#End If

' Mac: curl via MacScript (synchronous, returns stdout)
' Uses a unique sentinel string to separate the response body from the
' HTTP status code that curl appends via -w.
' Single-quoted curl args avoid JSON double-quote escaping entirely.
#If Mac Then
Private Function HttpMac(method As String, url As String, body As String) As String
    Const SEP As String = "|||HTTPSTATUS|||"
    Dim q As String: q = Chr(39)   ' single-quote char

    Dim cmd As String
    cmd = "curl -s -w " & q & SEP & "%{http_code}" & q
    cmd = cmd & " -X " & method
    cmd = cmd & " -H " & q & "Content-Type: application/json" & q
    cmd = cmd & " -H " & q & "Accept: application/json" & q

    If body <> "" Then
        ' Escape any single-quotes inside the body for shell single-quoting:
        ' replace each ' with '\''
        Dim sb As String
        sb = Replace(body, q, q & Chr(92) & q & q)
        cmd = cmd & " -d " & q & sb & q
    End If
    cmd = cmd & " " & q & url & q

    ' Wrap in AppleScript: only need to escape " as \" since we used ' for everything else
    Dim asCmd As String
    asCmd = Replace(cmd, Chr(34), Chr(92) & Chr(34))

    Dim raw As String
    On Error GoTo MacFail
    raw = MacScript("do shell script """ & asCmd & """")
    On Error GoTo 0

    Dim sepPos As Long: sepPos = InStr(raw, SEP)
    Dim status As String, resp As String
    If sepPos > 0 Then
        status = Trim(Mid(raw, sepPos + Len(SEP)))
        resp   = Left(raw, sepPos - 1)
    Else
        status = "0": resp = raw
    End If

    If Val(status) >= 200 And Val(status) < 300 Then
        HttpMac = resp
    Else
        Err.Raise vbObjectError + 500, , "HTTP " & status & Chr(10) & resp
    End If
    Exit Function
MacFail:
    Err.Raise vbObjectError + 500, , _
        "MacScript failed. If you are on macOS Ventura or later, " & _
        "go to System Settings > Privacy & Security > Automation and " & _
        "allow Excel to control the shell." & Chr(10) & Chr(10) & Err.Description
End Function
#End If

' ─── JSON — pure VBA, no COM objects (Windows + Mac) ─────────────────────────
' Extracts the value for a given key from a flat/shallow JSON object.
Private Function JGet(json As String, key As String) As String
    Dim srch As String: srch = Chr(34) & key & Chr(34) & ":"
    Dim p As Long: p = InStr(1, json, srch, vbBinaryCompare)
    If p = 0 Then Exit Function
    p = p + Len(srch)
    ' skip whitespace
    Do While p <= Len(json) And (Mid(json, p, 1) = " " Or Mid(json, p, 1) = Chr(9))
        p = p + 1
    Loop
    Dim ch As String: ch = Mid(json, p, 1)
    Select Case ch
        Case Chr(34)                    ' string value
            p = p + 1
            Dim e As Long: e = p
            Do While e <= Len(json)
                If Mid(json, e, 1) = Chr(92) Then   ' backslash — skip next char
                    e = e + 2
                ElseIf Mid(json, e, 1) = Chr(34) Then
                    Exit Do
                Else
                    e = e + 1
                End If
            Loop
            Dim v As String: v = Mid(json, p, e - p)
            ' unescape JSON sequences
            v = Replace(v, Chr(92) & Chr(92), Chr(1))  ' \\ -> placeholder
            v = Replace(v, Chr(92) & Chr(34), Chr(34)) ' \" -> "
            v = Replace(v, Chr(92) & "n",     Chr(10)) ' \n -> newline
            v = Replace(v, Chr(92) & "r",     "")      ' \r -> nothing
            v = Replace(v, Chr(92) & "t",     Chr(9))  ' \t -> tab
            v = Replace(v, Chr(1),            Chr(92)) ' placeholder -> \
            JGet = v
        Case "n": JGet = ""             ' null
        Case "t": JGet = "true"
        Case "f": JGet = "false"
        Case Else                       ' number
            Dim ne As Long: ne = p
            Do While ne <= Len(json)
                ch = Mid(json, ne, 1)
                If InStr(",}] " & Chr(9) & Chr(10), ch) > 0 Then Exit Do
                ne = ne + 1
            Loop
            JGet = Mid(json, p, ne - p)
    End Select
End Function

' Escape a string for embedding in a JSON double-quoted value
Private Function JEsc(s As String) As String
    s = Replace(s, Chr(92), Chr(92) & Chr(92))  ' \ -> \\
    s = Replace(s, Chr(34), Chr(92) & Chr(34))  ' " -> \"
    s = Replace(s, Chr(10), Chr(92) & "n")      ' LF -> \n
    s = Replace(s, Chr(13), "")                 ' CR -> (drop)
    JEsc = s
End Function

' Wrap a string in double quotes
Private Function Q(s As String) As String
    Q = Chr(34) & s & Chr(34)
End Function

' Build the JSON body for a POST/PUT initiative request
Private Function BuildBody(title As String, status As String, priority As String, _
    progress As Long, owner As String, dept As String, _
    desc As String, sd As String, ed As String) As String
    Dim p As String
    p = Q("title")    & ":" & Q(JEsc(title))
    p = p & "," & Q("status")    & ":" & Q(status)
    p = p & "," & Q("priority")  & ":" & Q(priority)
    p = p & "," & Q("progress")  & ":" & CStr(progress)
    If owner <> "" Then p = p & "," & Q("owner")       & ":" & Q(JEsc(owner))
    If dept  <> "" Then p = p & "," & Q("department")  & ":" & Q(JEsc(dept))
    If desc  <> "" Then p = p & "," & Q("description") & ":" & Q(JEsc(desc))
    If sd    <> "" Then p = p & "," & Q("startDate")   & ":" & Q(sd)
    If ed    <> "" Then p = p & "," & Q("endDate")     & ":" & Q(ed)
    BuildBody = "{" & p & "}"
End Function

' ─── Form sheet names & cell addresses ───────────────────────────────────────
' Two hidden sheets act as modal forms. VBA shows/hides them on demand.
Private Const INIT_FORM   As String = "Initiative Form"
Private Const UPDATE_FORM As String = "Update Form"

' Initiative Form — input cells in column B
Private Const IFC_TITLE  As String = "B3"
Private Const IFC_STATUS As String = "B4"
Private Const IFC_PRIO   As String = "B5"
Private Const IFC_PROG   As String = "B6"
Private Const IFC_OWNER  As String = "B7"
Private Const IFC_DEPT   As String = "B8"
Private Const IFC_DESC   As String = "B9"
Private Const IFC_SDATE  As String = "B10"
Private Const IFC_EDATE  As String = "B11"
' State stored off-screen in column G (hidden from users)
Private Const IFC_MODE   As String = "G1"
Private Const IFC_ID     As String = "G2"

' Update Form — input cells
Private Const UFC_NM     As String = "B3"
Private Const UFC_NOTE   As String = "B4"
Private Const UFC_AUTHOR As String = "B6"
Private Const UFC_ID     As String = "G1"

' ─── Row / sheet helpers ──────────────────────────────────────────────────────
Private Function RowId(ws As Worksheet, row As Long) As String
    On Error Resume Next
    RowId = ws.Cells(row, 1).Comment.Text
    On Error GoTo 0
End Function

Private Function InitWS() As Worksheet
    On Error Resume Next
    Set InitWS = ThisWorkbook.Sheets("Initiatives")
    On Error GoTo 0
    If InitWS Is Nothing Then
        MsgBox "Initiatives sheet not found.", vbExclamation
    End If
End Function

Private Function StatusLabel(s As String) As String
    Select Case LCase(Trim(s))
        Case "on_track":    StatusLabel = "On Track"
        Case "at_risk":     StatusLabel = "At Risk"
        Case "delayed":     StatusLabel = "Delayed"
        Case "completed":   StatusLabel = "Completed"
        Case "not_started": StatusLabel = "Not Started"
        Case Else:          StatusLabel = s
    End Select
End Function

Private Function StatusCode(label As String) As String
    Select Case LCase(Trim(label))
        Case "on track":    StatusCode = "on_track"
        Case "at risk":     StatusCode = "at_risk"
        Case "delayed":     StatusCode = "delayed"
        Case "completed":   StatusCode = "completed"
        Case "not started": StatusCode = "not_started"
        Case Else:          StatusCode = LCase(Replace(Trim(label), " ", "_"))
    End Select
End Function

Private Function CurrentUser() As String
#If Mac Then
    CurrentUser = Environ("USER")
#Else
    CurrentUser = Environ("USERNAME")
#End If
    If CurrentUser = "" Then CurrentUser = "User"
End Function

Private Sub WriteInitRow(ws As Worksheet, r As Long, _
    id As String, rowNum As Long, _
    title As String, status As String, priority As String, progress As Long, _
    owner As String, dept As String, sd As String, ed As String, updatedAt As String)
    ws.Cells(r, 1).Value  = rowNum
    ws.Cells(r, 2).Value  = title
    ws.Cells(r, 3).Value  = StatusLabel(status)
    ws.Cells(r, 4).Value  = StrConv(priority, vbProperCase)
    ws.Cells(r, 5).Value  = progress / 100
    ws.Cells(r, 5).NumberFormat = "0%"
    ws.Cells(r, 6).Value  = IIf(Trim(owner) = "", Chr(8212), owner)
    ws.Cells(r, 7).Value  = IIf(Trim(dept)  = "", Chr(8212), dept)
    ws.Cells(r, 8).Value  = Left(sd, 10)
    ws.Cells(r, 9).Value  = Left(ed, 10)
    ws.Cells(r, 10).Value = IIf(updatedAt = "", Format(Now(), "mmm dd, yyyy"), updatedAt)
    If id <> "" Then
        On Error Resume Next
        ws.Cells(r, 1).Comment.Delete
        ws.Cells(r, 1).AddComment id
        ws.Cells(r, 1).Comment.Visible = False
        On Error GoTo 0
    End If
End Sub

' ─── Initiative Form ──────────────────────────────────────────────────────────
' Clicking Create or Edit opens this hidden sheet. User fills the fields and
' clicks Save — the API is called and the Initiatives sheet updates in-place.

Public Sub ShowInitForm(mode As String, id As String)
    Dim fws As Worksheet
    On Error Resume Next
    Set fws = ThisWorkbook.Sheets(INIT_FORM)
    On Error GoTo 0
    If fws Is Nothing Then
        MsgBox "Initiative Form sheet not found." & Chr(10) & _
               "Run CreateButtons to rebuild it.", vbExclamation
        Exit Sub
    End If

    fws.Range(IFC_MODE).Value = mode
    fws.Range(IFC_ID).Value   = id
    fws.Cells(1, 1).Value = IIf(mode = "edit", _
        "  Edit Initiative", "  Create New Initiative")

    If mode = "edit" And id <> "" Then
        Dim json As String: json = Http("GET", "/initiatives/" & id)
        fws.Range(IFC_TITLE).Value  = JGet(json, "title")
        fws.Range(IFC_STATUS).Value = StatusLabel(JGet(json, "status"))
        fws.Range(IFC_PRIO).Value   = StrConv(JGet(json, "priority"), vbProperCase)
        fws.Range(IFC_PROG).Value   = Val(JGet(json, "progress"))
        fws.Range(IFC_OWNER).Value  = JGet(json, "owner")
        fws.Range(IFC_DEPT).Value   = JGet(json, "department")
        fws.Range(IFC_DESC).Value   = JGet(json, "description")
        fws.Range(IFC_SDATE).Value  = Left(JGet(json, "startDate"), 10)
        fws.Range(IFC_EDATE).Value  = Left(JGet(json, "endDate"), 10)
    Else
        fws.Range(IFC_TITLE).Value  = ""
        fws.Range(IFC_STATUS).Value = "On Track"
        fws.Range(IFC_PRIO).Value   = "Medium"
        fws.Range(IFC_PROG).Value   = 0
        fws.Range(IFC_OWNER).Value  = ""
        fws.Range(IFC_DEPT).Value   = ""
        fws.Range(IFC_DESC).Value   = ""
        fws.Range(IFC_SDATE).Value  = ""
        fws.Range(IFC_EDATE).Value  = ""
    End If

    fws.Visible = True
    fws.Activate
    fws.Range(IFC_TITLE).Select
End Sub

Public Sub SaveInitForm()
    On Error GoTo Fail
    Dim fws As Worksheet: Set fws = ThisWorkbook.Sheets(INIT_FORM)

    Dim mode     As String: mode     = Trim(fws.Range(IFC_MODE).Value)
    Dim id       As String: id       = Trim(fws.Range(IFC_ID).Value)
    Dim title    As String: title    = Trim(fws.Range(IFC_TITLE).Value)
    Dim status   As String: status   = StatusCode(fws.Range(IFC_STATUS).Value)
    Dim priority As String: priority = LCase(Trim(fws.Range(IFC_PRIO).Value))
    Dim progress As Long:   progress = CLng(Val(fws.Range(IFC_PROG).Value))
    Dim owner    As String: owner    = Trim(fws.Range(IFC_OWNER).Value)
    Dim dept     As String: dept     = Trim(fws.Range(IFC_DEPT).Value)
    Dim desc     As String: desc     = Trim(fws.Range(IFC_DESC).Value)
    Dim sd       As String: sd       = Trim(fws.Range(IFC_SDATE).Value)
    Dim ed       As String: ed       = Trim(fws.Range(IFC_EDATE).Value)

    If title = "" Then
        MsgBox "Title is required.", vbExclamation, "Missing Field"
        fws.Range(IFC_TITLE).Select: Exit Sub
    End If
    If status = "" Then
        MsgBox "Status is required.", vbExclamation, "Missing Field"
        fws.Range(IFC_STATUS).Select: Exit Sub
    End If
    If progress < 0  Then progress = 0
    If progress > 100 Then progress = 100

    Dim ws As Worksheet: Set ws = ThisWorkbook.Sheets("Initiatives")
    Dim body As String
    body = BuildBody(title, status, priority, progress, owner, dept, desc, sd, ed)

    If mode = "edit" Then
        Http "PUT", "/initiatives/" & id, body
        Dim r As Long
        For r = 3 To ws.Cells(ws.Rows.Count, 2).End(xlUp).Row
            If CStr(RowId(ws, r)) = CStr(id) Then
                Call WriteInitRow(ws, r, id, CLng(ws.Cells(r, 1).Value), _
                                  title, status, priority, progress, owner, dept, _
                                  sd, ed, Format(Now(), "mmm dd, yyyy"))
                Exit For
            End If
        Next r
        fws.Visible = False
        ws.Activate
        MsgBox "Initiative updated.", vbInformation, "Saved"
    Else
        Dim resp As String: resp = Http("POST", "/initiatives", body)
        Dim newId   As String:  newId   = JGet(resp, "id")
        Dim lastRow As Long:    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row
        Dim newRow  As Long:    newRow  = lastRow + 1
        Call WriteInitRow(ws, newRow, newId, newRow - 1, title, status, priority, _
                         progress, owner, dept, sd, ed, "")
        ws.Rows(newRow).RowHeight = 20
        fws.Visible = False
        ws.Activate
        ws.Cells(newRow, 1).Select
        MsgBox "Initiative created.", vbInformation, "Created"
    End If
    Exit Sub
Fail:
    MsgBox "Error: " & Err.Description, vbCritical, "Save Failed"
End Sub

Public Sub CancelInitForm()
    On Error Resume Next
    ThisWorkbook.Sheets(INIT_FORM).Visible = False
    ThisWorkbook.Sheets("Initiatives").Activate
    On Error GoTo 0
End Sub

' ─── Update Form ──────────────────────────────────────────────────────────────

Public Sub ShowUpdateForm(id As String, nm As String)
    Dim fws As Worksheet
    On Error Resume Next
    Set fws = ThisWorkbook.Sheets(UPDATE_FORM)
    On Error GoTo 0
    If fws Is Nothing Then
        MsgBox "Update Form sheet not found." & Chr(10) & _
               "Run CreateButtons to rebuild it.", vbExclamation
        Exit Sub
    End If

    fws.Range(UFC_ID).Value     = id
    fws.Range(UFC_NM).Value     = nm
    fws.Range(UFC_NOTE).Value   = ""
    fws.Range(UFC_AUTHOR).Value = CurrentUser()

    fws.Visible = True
    fws.Activate
    fws.Range(UFC_NOTE).Select
End Sub

Public Sub SaveUpdateForm()
    On Error GoTo Fail
    Dim fws As Worksheet: Set fws = ThisWorkbook.Sheets(UPDATE_FORM)

    Dim id     As String: id     = Trim(fws.Range(UFC_ID).Value)
    Dim nm     As String: nm     = Trim(fws.Range(UFC_NM).Value)
    Dim note   As String: note   = Trim(fws.Range(UFC_NOTE).Value)
    Dim author As String: author = Trim(fws.Range(UFC_AUTHOR).Value)

    If note = "" Then
        MsgBox "Please enter a note.", vbExclamation, "Missing Field"
        fws.Range(UFC_NOTE).Select: Exit Sub
    End If
    If author = "" Then author = "Unknown"

    Dim body As String
    body = "{" & Q("note")         & ":" & Q(JEsc(note)) & _
           "," & Q("author")       & ":" & Q(JEsc(author)) & _
           "," & Q("initiativeId") & ":" & Q(JEsc(id)) & "}"
    Http "POST", "/initiatives/" & id & "/updates", body

    On Error Resume Next
    Dim ws3 As Worksheet: Set ws3 = ThisWorkbook.Sheets("Updates Log")
    On Error GoTo Fail
    If Not ws3 Is Nothing Then
        ws3.Rows(3).Insert Shift:=xlDown
        Dim lastNum As Long
        On Error Resume Next: lastNum = CLng(ws3.Cells(4, 1).Value): On Error GoTo 0
        ws3.Cells(3, 1).Value = lastNum + 1
        ws3.Cells(3, 2).Value = nm
        ws3.Cells(3, 3).Value = note
        ws3.Cells(3, 4).Value = author
        ws3.Cells(3, 5).Value = Format(Now(), "mmm dd, yyyy")
        ws3.Rows(3).RowHeight = 20
    End If

    fws.Visible = False
    On Error Resume Next: ThisWorkbook.Sheets("Initiatives").Activate: On Error GoTo 0
    MsgBox "Update posted.", vbInformation, "Posted"
    Exit Sub
Fail:
    MsgBox "Error: " & Err.Description, vbCritical, "Failed"
End Sub

Public Sub CancelUpdateForm()
    On Error Resume Next
    ThisWorkbook.Sheets(UPDATE_FORM).Visible = False
    ThisWorkbook.Sheets("Initiatives").Activate
    On Error GoTo 0
End Sub

' ─── PUBLIC MACROS ────────────────────────────────────────────────────────────

Public Sub TestConnection()
    On Error GoTo Fail
    Http "GET", "/initiatives?limit=1"
    MsgBox "Connected!" & Chr(10) & "API: " & ApiBase(), vbInformation, "Connection OK"
    Exit Sub
Fail:
    MsgBox "Connection failed." & Chr(10) & Chr(10) & _
           "URL tried: " & ApiBase() & Chr(10) & Chr(10) & _
           Err.Description & Chr(10) & Chr(10) & _
           "Update the URL in the Config sheet (cell B4).", _
           vbCritical, "Connection Failed"
End Sub

' Opens the Initiative Form sheet ready to create a new initiative.
Public Sub CreateInitiative()
    ShowInitForm "create", ""
End Sub

' Opens the Initiative Form sheet pre-filled with the selected row's data.
Public Sub EditInitiative()
    Dim ws As Worksheet: Set ws = InitWS()
    If ws Is Nothing Then Exit Sub
    Dim r As Long: r = ActiveCell.Row
    If r <= 2 Then
        MsgBox "Click on a data row first (row 3 or below).", vbExclamation: Exit Sub
    End If
    Dim id As String: id = RowId(ws, r)
    If id = "" Then
        MsgBox "Initiative ID not found." & Chr(10) & _
               "Re-export from the app to embed IDs.", vbExclamation: Exit Sub
    End If
    ShowInitForm "edit", id
End Sub

' Confirms then deletes the selected initiative from the API and the sheet.
Public Sub DeleteInitiative()
    On Error GoTo Fail
    Dim ws As Worksheet: Set ws = InitWS()
    If ws Is Nothing Then Exit Sub
    Dim r As Long: r = ActiveCell.Row
    If r <= 2 Then
        MsgBox "Click on a data row first.", vbExclamation: Exit Sub
    End If
    Dim id As String: id = RowId(ws, r)
    If id = "" Then
        MsgBox "ID not found. Re-export from the app.", vbExclamation: Exit Sub
    End If
    Dim nm As String: nm = ws.Cells(r, 2).Value
    If MsgBox("Permanently delete """ & nm & """?" & Chr(10) & Chr(10) & _
              "All updates for this initiative will also be deleted." & Chr(10) & _
              "This cannot be undone.", _
              vbQuestion + vbYesNo + vbDefaultButton2, "Confirm Delete") <> vbYes Then
        Exit Sub
    End If
    Http "DELETE", "/initiatives/" & id
    ws.Rows(r).Delete
    MsgBox "Deleted.", vbInformation, "Done"
    Exit Sub
Fail:
    MsgBox "Error: " & Err.Description, vbCritical, "Delete Failed"
End Sub

' Opens the Update Form sheet for the selected initiative.
Public Sub AddUpdate()
    Dim ws As Worksheet: Set ws = InitWS()
    If ws Is Nothing Then Exit Sub
    Dim r As Long: r = ActiveCell.Row
    If r <= 2 Then
        MsgBox "Click on a data row first.", vbExclamation: Exit Sub
    End If
    Dim id As String: id = RowId(ws, r)
    If id = "" Then
        MsgBox "ID not found. Re-export from the app.", vbExclamation: Exit Sub
    End If
    ShowUpdateForm id, ws.Cells(r, 2).Value
End Sub

' ─── Buttons ──────────────────────────────────────────────────────────────────

' Runs on file open — recreates sidebar buttons if missing.
Public Sub Auto_Open()
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Initiatives")
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub
    Dim shp As Shape
    For Each shp In ws.Shapes
        If Left(shp.Name, 9) = "MacroBtn_" Then Exit Sub
    Next shp
    CreateButtons
End Sub

' CreateButtons builds the sidebar on the Initiatives sheet AND adds Save/Cancel
' buttons to the two form sheets. Run once after importing the module; buttons
' are saved in the workbook and survive re-open.
Public Sub CreateButtons()
    ' ── Initiatives sheet sidebar ─────────────────────────────────────────────
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Initiatives")
    On Error GoTo 0
    If ws Is Nothing Then MsgBox "Initiatives sheet not found.", vbExclamation: Exit Sub

    Dim shp As Shape, toDelete() As String, n As Long: n = 0
    For Each shp In ws.Shapes
        If Left(shp.Name, 9) = "MacroBtn_" Then
            ReDim Preserve toDelete(n): toDelete(n) = shp.Name: n = n + 1
        End If
    Next shp
    Dim j As Long
    For j = 0 To n - 1: ws.Shapes(toDelete(j)).Delete: Next j

    ws.Columns("L:L").ColumnWidth = 20

    Dim defs(4, 2) As Variant
    defs(0, 0) = "TestConnection":   defs(0, 1) = "Test Connection":   defs(0, 2) = RGB(71, 85, 105)
    defs(1, 0) = "CreateInitiative": defs(1, 1) = "Create Initiative":  defs(1, 2) = RGB(21, 128, 61)
    defs(2, 0) = "EditInitiative":   defs(2, 1) = "Edit Selected Row":  defs(2, 2) = RGB(29, 78, 216)
    defs(3, 0) = "DeleteInitiative": defs(3, 1) = "Delete Selected":    defs(3, 2) = RGB(185, 28, 28)
    defs(4, 0) = "AddUpdate":        defs(4, 1) = "Add Update Note":     defs(4, 2) = RGB(15, 37, 68)

    Dim btnLeft As Double:   btnLeft   = ws.Range("L2").Left + 3
    Dim btnWidth As Double:  btnWidth  = ws.Range("L2").Width - 6
    Dim btnHeight As Double: btnHeight = 26
    Dim gap As Double:       gap       = 5
    Dim s As Shape
    Dim i As Integer
    For i = 0 To 4
        Dim macroName As String: macroName = CStr(defs(i, 0))
        Dim caption   As String: caption   = CStr(defs(i, 1))
        Dim fillColor As Long:   fillColor = CLng(defs(i, 2))
        Dim btnTop    As Double: btnTop    = ws.Range("A2").Top + 2 + i * (btnHeight + gap)
        Set s = ws.Shapes.AddShape(5, btnLeft, btnTop, btnWidth, btnHeight)
        With s
            .Name = "MacroBtn_" & macroName: .OnAction = macroName
            .Fill.ForeColor.RGB = fillColor: .Fill.Solid: .Line.Visible = False
            With .TextFrame
                .MarginLeft = 0: .MarginRight = 0: .MarginTop = 0: .MarginBottom = 0
                .HorizontalAlignment = 2: .VerticalAlignment = 2
                .Characters.Text = caption
                With .Characters.Font: .Color = RGB(255,255,255): .Bold = True: .Size = 9: End With
            End With
        End With
    Next i

    ' ── Initiative Form sheet buttons ─────────────────────────────────────────
    Dim ifs As Worksheet
    On Error Resume Next: Set ifs = ThisWorkbook.Sheets(INIT_FORM): On Error GoTo 0
    If Not ifs Is Nothing Then
        ' Remove old form buttons
        Dim fd() As String: Dim fn As Long: fn = 0
        For Each shp In ifs.Shapes
            If Left(shp.Name, 8) = "FormBtn_" Then
                ReDim Preserve fd(fn): fd(fn) = shp.Name: fn = fn + 1
            End If
        Next shp
        For j = 0 To fn - 1: ifs.Shapes(fd(j)).Delete: Next j

        Dim iBtnLeft  As Double: iBtnLeft  = ifs.Range("B13").Left
        Dim iBtnTop   As Double: iBtnTop   = ifs.Range("B13").Top + 4

        ' Save (green)
        Set s = ifs.Shapes.AddShape(5, iBtnLeft, iBtnTop, 110, 28)
        With s
            .Name = "FormBtn_Save": .OnAction = "SaveInitForm"
            .Fill.ForeColor.RGB = RGB(21, 128, 61): .Fill.Solid: .Line.Visible = False
            With .TextFrame
                .MarginLeft = 0: .MarginRight = 0: .MarginTop = 0: .MarginBottom = 0
                .HorizontalAlignment = 2: .VerticalAlignment = 2
                .Characters.Text = "Save"
                With .Characters.Font: .Color = RGB(255,255,255): .Bold = True: .Size = 10: End With
            End With
        End With

        ' Cancel (slate)
        Set s = ifs.Shapes.AddShape(5, iBtnLeft + 118, iBtnTop, 110, 28)
        With s
            .Name = "FormBtn_Cancel": .OnAction = "CancelInitForm"
            .Fill.ForeColor.RGB = RGB(71, 85, 105): .Fill.Solid: .Line.Visible = False
            With .TextFrame
                .MarginLeft = 0: .MarginRight = 0: .MarginTop = 0: .MarginBottom = 0
                .HorizontalAlignment = 2: .VerticalAlignment = 2
                .Characters.Text = "Cancel"
                With .Characters.Font: .Color = RGB(255,255,255): .Bold = True: .Size = 10: End With
            End With
        End With
    End If

    ' ── Update Form sheet buttons ─────────────────────────────────────────────
    Dim ufs As Worksheet
    On Error Resume Next: Set ufs = ThisWorkbook.Sheets(UPDATE_FORM): On Error GoTo 0
    If Not ufs Is Nothing Then
        Dim ud() As String: Dim un As Long: un = 0
        For Each shp In ufs.Shapes
            If Left(shp.Name, 8) = "FormBtn_" Then
                ReDim Preserve ud(un): ud(un) = shp.Name: un = un + 1
            End If
        Next shp
        For j = 0 To un - 1: ufs.Shapes(ud(j)).Delete: Next j

        Dim uBtnLeft As Double: uBtnLeft = ufs.Range("B8").Left
        Dim uBtnTop  As Double: uBtnTop  = ufs.Range("B8").Top + 4

        ' Post (blue)
        Set s = ufs.Shapes.AddShape(5, uBtnLeft, uBtnTop, 130, 28)
        With s
            .Name = "FormBtn_Post": .OnAction = "SaveUpdateForm"
            .Fill.ForeColor.RGB = RGB(29, 78, 216): .Fill.Solid: .Line.Visible = False
            With .TextFrame
                .MarginLeft = 0: .MarginRight = 0: .MarginTop = 0: .MarginBottom = 0
                .HorizontalAlignment = 2: .VerticalAlignment = 2
                .Characters.Text = "Post Update"
                With .Characters.Font: .Color = RGB(255,255,255): .Bold = True: .Size = 10: End With
            End With
        End With

        ' Cancel (slate)
        Set s = ufs.Shapes.AddShape(5, uBtnLeft + 138, uBtnTop, 110, 28)
        With s
            .Name = "FormBtn_CancelU": .OnAction = "CancelUpdateForm"
            .Fill.ForeColor.RGB = RGB(71, 85, 105): .Fill.Solid: .Line.Visible = False
            With .TextFrame
                .MarginLeft = 0: .MarginRight = 0: .MarginTop = 0: .MarginBottom = 0
                .HorizontalAlignment = 2: .VerticalAlignment = 2
                .Characters.Text = "Cancel"
                With .Characters.Font: .Color = RGB(255,255,255): .Bold = True: .Size = 10: End With
            End With
        End With
    End If

    MsgBox "Buttons created on all sheets." & Chr(10) & _
           "Save as .xlsm to keep them.", vbInformation, "Done"
End Sub
'''

# ─── WORKBOOK ─────────────────────────────────────────────────────────────────
OUT     = "/home/runner/workspace/initiative_tracker.xlsx"
BAS_OUT = "/home/runner/workspace/initiative_tracker_macros.bas"
wb  = xlsxwriter.Workbook(OUT, {"nan_inf_to_errors": True})
wb.set_properties({"title": "Initiative Tracker", "author": "Leadership Portal"})

# colour palette
NAVY  = "#0F2544"; NAVY2 = "#1B3A6B"; WHITE = "#FFFFFF"
STRIPE = "#E8F0FE"; BORDER = "#94A3B8"

STATUS_STYLE = {
    "on_track":    ("#DCFCE7", "#14532D", "#16A34A", "#FFFFFF"),
    "at_risk":     ("#FEF9C3", "#713F12", "#D97706", "#FFFFFF"),
    "delayed":     ("#FEE2E2", "#7F1D1D", "#DC2626", "#FFFFFF"),
    "completed":   ("#DBEAFE", "#1E3A8A", "#2563EB", "#FFFFFF"),
    "not_started": ("#F1F5F9", "#334155", "#64748B", "#FFFFFF"),
}
STATUS_LABEL = {
    "on_track": "On Track", "at_risk": "At Risk",
    "delayed": "Delayed", "completed": "Completed", "not_started": "Not Started",
}
PRIORITY_STYLE = {
    "High":   ("#FEE2E2", "#DC2626"),
    "Medium": ("#FEF9C3", "#D97706"),
    "Low":    ("#F1F5F9", "#64748B"),
}

_fmt_cache = {}
def F(**kw):
    base = {"font_name": "Calibri", "font_size": 10, "valign": "vcenter"}
    base.update(kw)
    key = tuple(sorted(base.items()))
    if key not in _fmt_cache:
        _fmt_cache[key] = wb.add_format(base)
    return _fmt_cache[key]

def fd(d):
    return d.strftime("%b %d, %Y") if d and hasattr(d, "strftime") else (str(d) if d else "")

# ─── TAB: Config ──────────────────────────────────────────────────────────────
wsc = wb.add_worksheet("Config")
wsc.hide_gridlines(2)
wsc.set_column("A:A", 24)
wsc.set_column("B:B", 52)
wsc.set_row(0, 40)
wsc.merge_range(0, 0, 0, 1, "  VBA Configuration",
    F(font_size=16, bold=True, bg_color=NAVY, font_color=WHITE, align="left", indent=1))
wsc.set_row(1, 8)

wsc.write(2, 0, "Setting",
    F(bold=True, bg_color=NAVY2, font_color=WHITE, border=1, border_color=NAVY, align="center"))
wsc.write(2, 1, "Value",
    F(bold=True, bg_color=NAVY2, font_color=WHITE, border=1, border_color=NAVY, align="center"))
wsc.set_row(2, 22)

wsc.write(3, 0, "API Base URL",
    F(bold=True, bg_color="#E8EEF9", font_color=NAVY, border=1, border_color=BORDER))
wsc.write(3, 1, "http://localhost/api",
    F(font_color="#1D4ED8", bg_color="#FFFFFF", border=1, border_color=BORDER,
      underline=True))
wsc.set_row(3, 22)
wsc.set_row(4, 8)

instructions = [
    ("STEP 1 — Import macros (one-time setup)",
     "Open the VBA editor:  Windows → Alt+F11   |   Mac → Option+F11  (or Tools > Macro > Visual Basic Editor)\n"
     "Then: File → Import File → select  initiative_tracker_macros.bas  from the same folder as this file.\n"
     "Close the editor. Save this file as .xlsm (macro-enabled workbook) when prompted."),
    ("STEP 2 — Set the API URL",
     "Edit cell B4 above with your API address.\n"
     "Local (app running on this machine):  http://localhost/api\n"
     "Deployed:  https://your-app.replit.app/api"),
    ("STEP 3 — Run TestConnection",
     "Windows: Alt+F8  →  TestConnection  →  Run\n"
     "Mac:  Tools  →  Macro  →  Macros…  →  TestConnection  →  Run\n"
     "A popup saying 'Connected!' confirms everything is working."),
    ("CreateInitiative",
     "Creates a new initiative via dialog prompts. Re-export from the app to see it in this file."),
    ("EditInitiative",
     "Click any data row in the Initiatives sheet, then run this macro to edit that initiative."),
    ("DeleteInitiative",
     "Click the initiative row to delete, then run. Shows a confirmation dialog before deleting."),
    ("AddUpdate",
     "Click an initiative row in the Initiatives sheet, then run to post a progress note."),
    ("Macro security (Windows)",
     "If macros are blocked: File → Options → Trust Center → Macro Settings → Enable all macros."),
    ("Macro security (Mac)",
     "If macros are blocked: Excel menu → Preferences → Security → Enable all macros."),
]
for i, (k, v) in enumerate(instructions):
    r = 5 + i
    bg = STRIPE if i % 2 == 0 else WHITE
    wsc.write(r, 0, k, F(bold=True, bg_color=bg, font_color=NAVY, border=1, border_color=BORDER,
                          text_wrap=True, indent=1))
    wsc.write(r, 1, v, F(bg_color=bg, font_color="#374151", border=1, border_color=BORDER,
                          text_wrap=True, indent=1))
    wsc.set_row(r, 30)

# ─── TAB: Summary ─────────────────────────────────────────────────────────────
ws1 = wb.add_worksheet("Summary")
ws1.hide_gridlines(2)
for col, w in [("A",2),("B",20),("C",14),("D",14),("E",14),("F",14),("G",14),("H",14),("I",2)]:
    ws1.set_column(f"{col}:{col}", w)

ws1.merge_range(1, 1, 1, 7, "Executive Summary",
    F(font_size=22, bold=True, bg_color=NAVY, font_color=WHITE,
      align="left", indent=1, left=5, left_color="#34D399"))
ws1.set_row(1, 46)
ws1.merge_range(2, 1, 2, 7, f"Data as of {NOW}",
    F(font_size=11, italic=True, bg_color=NAVY2, font_color="#93C5FD", align="left", indent=1))
ws1.set_row(2, 22)
ws1.set_row(3, 14)

kpis = [
    ("TOTAL",       summary[0],         NAVY,      WHITE),
    ("ON TRACK",    summary[1],         "#15803D",  WHITE),
    ("AT RISK",     summary[2],         "#B45309",  WHITE),
    ("DELAYED",     summary[3],         "#B91C1C",  WHITE),
    ("COMPLETED",   summary[4],         "#1D4ED8",  WHITE),
    ("AVG PROGRESS",f"{summary[6]}%",   "#374151",  WHITE),
]
for i, (label, value, bg, fg) in enumerate(kpis):
    col = i + 1
    ws1.merge_range(4, col, 5, col, value,
        F(font_size=34, bold=True, bg_color=bg, font_color=fg,
          align="center", valign="bottom",
          top=5, top_color=bg, left=1, left_color=WHITE, right=1, right_color=WHITE))
    ws1.write(6, col, label,
        F(font_size=9, bold=True, bg_color=bg, font_color=fg,
          align="center", bottom=5, bottom_color=bg,
          left=1, left_color=WHITE, right=1, right_color=WHITE))
ws1.set_row(4, 44); ws1.set_row(5, 4); ws1.set_row(6, 24); ws1.set_row(7, 18)

ws1.merge_range(8, 1, 8, 7, "  Department Breakdown",
    F(bold=True, font_size=11, bg_color=NAVY2, font_color=WHITE,
      align="left", left=5, left_color="#60A5FA"))
ws1.set_row(8, 22)

for ci, h in enumerate(["Department","Total","On Track","At Risk","Delayed","Completed","Avg %"]):
    ws1.write(9, ci+1, h,
        F(bold=True, bg_color=NAVY, font_color=WHITE,
          align="center" if ci > 0 else "left", indent=1 if ci==0 else 0,
          border=1, border_color=NAVY2))
ws1.set_row(9, 22)

for ri, row in enumerate(by_dept):
    r  = 10 + ri
    bg = STRIPE if ri % 2 == 0 else WHITE
    dept, total, on_t, at_r, dly, comp, avg = row
    vals = [dept, total, on_t, at_r, dly, comp, f"{avg}%"]
    highlights = [None, None, "#15803D", "#B45309", "#B91C1C", "#1D4ED8", None]
    for ci, val in enumerate(vals):
        fg   = highlights[ci] if (highlights[ci] and isinstance(val, int) and val > 0) else "#0F172A"
        bold = fg != "#0F172A"
        ws1.write(r, ci+1, val,
            F(bg_color=bg, font_color=fg, bold=bold,
              align="left" if ci==0 else "center", indent=1 if ci==0 else 0,
              bottom=1, bottom_color=BORDER, left=1, left_color=BORDER, right=1, right_color=BORDER))
    ws1.set_row(r, 20)

chart_end = 10 + len(by_dept)

# Hidden chart data
for i, (lbl, val) in enumerate(zip(["On Track","At Risk","Delayed","Completed","Not Started"],
                                    [summary[1],summary[2],summary[3],summary[4],summary[5]])):
    ws1.write(1+i, 10, lbl); ws1.write(1+i, 11, val)

pie = wb.add_chart({"type": "pie"})
pie.set_title({"name": "Status Distribution",
               "name_font": {"bold": True, "size": 12, "color": NAVY}})
pie.add_series({
    "categories": ["Summary", 2, 10, 6, 10],
    "values":     ["Summary", 2, 11, 6, 11],
    "data_labels": {"percentage": True, "category": True, "separator": "\n", "font": {"size": 9}},
    "points": [{"fill": {"color": c}} for c in
               ["#22C55E","#F59E0B","#EF4444","#3B82F6","#94A3B8"]],
})
pie.set_size({"width": 380, "height": 280})
pie.set_legend({"position": "bottom", "font": {"size": 9}})
pie.set_chartarea({"border": {"none": True}})
ws1.insert_chart(1, 9, pie, {"x_offset": 5, "y_offset": 5})

bar = wb.add_chart({"type": "column"})
bar.set_title({"name": "Initiatives by Department",
               "name_font": {"bold": True, "size": 12, "color": NAVY}})
bar.add_series({
    "categories": ["Summary", 10, 1, chart_end-1, 1],
    "values":     ["Summary", 10, 2, chart_end-1, 2],
    "fill": {"color": NAVY2},
    "data_labels": {"value": True, "font": {"size": 9, "bold": True, "color": WHITE}},
})
bar.set_legend({"none": True})
bar.set_size({"width": 380, "height": 280})
bar.set_chartarea({"border": {"none": True}})
ws1.insert_chart(18, 9, bar, {"x_offset": 5, "y_offset": 5})

# ─── TAB: Initiatives ────────────────────────────────────────────────────────
ws2 = wb.add_worksheet("Initiatives")
ws2.hide_gridlines(2)
ws2.freeze_panes(2, 0)

I_HDR   = ["#", "Title", "Status", "Priority", "Progress %",
           "Owner", "Department", "Start", "End", "Updated"]
I_W     = [4, 38, 13, 12, 13, 20, 18, 12, 12, 14]
I_ALIGN = ["center","left","center","center","center","left","left","center","center","center"]

for ci, w in enumerate(I_W):
    ws2.set_column(ci, ci, w)

ws2.merge_range(0, 0, 0, len(I_HDR)-1,
    f"  All Initiatives  ·  {len(initiatives)} total  ·  "
    f"Import macros from initiative_tracker_macros.bas then run: "
    f"CreateInitiative | EditInitiative | DeleteInitiative | AddUpdate",
    F(font_size=11, bold=True, bg_color=NAVY, font_color=WHITE,
      align="left", left=5, left_color="#22C55E"))
ws2.set_row(0, 30)

for ci, h in enumerate(I_HDR):
    ws2.write(1, ci, h,
        F(bold=True, bg_color=NAVY, font_color=WHITE,
          align=I_ALIGN[ci], indent=1 if I_ALIGN[ci]=="left" else 0,
          border=1, border_color=NAVY2))
ws2.set_row(1, 22)
ws2.autofilter(1, 0, 1, len(I_HDR)-1)

for ri, row_data in enumerate(initiatives):
    iid, title, desc, status, progress, priority, owner, dept, sd, ed, ca, ua = row_data
    r   = ri + 2
    rbg, rtxt, pbg, ptxt = STATUS_STYLE.get(status, ("#F1F5F9","#334155","#64748B","#FFFFFF"))
    sl  = STATUS_LABEL.get(status, status)
    pl  = priority.capitalize()
    pri_bg, pri_txt = PRIORITY_STYLE.get(pl, ("#F1F5F9","#64748B"))

    vals = [ri+1, title, sl, pl, progress/100,
            owner or "—", dept or "—", fd(sd), fd(ed), fd(ua)]

    for ci, val in enumerate(vals):
        align  = I_ALIGN[ci]
        indent = 1 if align == "left" else 0
        if ci == 0:
            ws2.write(r, ci, val, F(font_color="#9CA3AF", bg_color=rbg,
                align="center", bottom=1, bottom_color=BORDER))
        elif ci == 1:
            ws2.write(r, ci, val, F(bold=True, font_color="#0F172A", bg_color=rbg,
                align="left", indent=1, bottom=1, bottom_color=BORDER))
        elif ci == 2:
            ws2.write(r, ci, val, F(bold=True, font_size=9,
                bg_color=pbg, font_color=ptxt, align="center",
                border=2, border_color=pbg))
        elif ci == 3:
            ws2.write(r, ci, val, F(bold=True, font_size=9,
                bg_color=pri_bg, font_color=pri_txt, align="center",
                border=1, border_color=pri_txt))
        elif ci == 4:
            ws2.write(r, ci, val, F(bold=True, font_color=NAVY2, bg_color=rbg,
                align="center", num_format="0%", bottom=1, bottom_color=BORDER))
        else:
            ws2.write(r, ci, val, F(font_color="#475569", bg_color=rbg,
                align=align, indent=indent, bottom=1, bottom_color=BORDER))

    # Store initiative ID as a comment on the row-number cell so VBA can find it
    ws2.write_comment(r, 0, str(iid), {"visible": False, "width": 120, "height": 40})
    ws2.set_row(r, 20)

last_i = len(initiatives) + 1
ws2.conditional_format(2, 4, last_i, 4, {
    "type": "data_bar", "bar_color": NAVY2,
    "bar_solid": True, "bar_border_color": NAVY, "data_bar_2010": True,
})

# Status legend
leg = last_i + 2
ws2.write(leg, 0, "  Row colour = status:",
    F(italic=True, font_size=9, font_color="#9CA3AF", bg_color="#F8FAFC"))
for ci, (status, (rbg, rtxt, pbg, ptxt)) in enumerate(STATUS_STYLE.items()):
    ws2.write(leg, ci+1, f"  {STATUS_LABEL[status]}",
        F(bold=True, font_size=9, bg_color=rbg, font_color=rtxt,
          border=1, border_color=rbg))
ws2.set_row(leg, 18)

# ─── TAB: Updates Log ─────────────────────────────────────────────────────────
ws3 = wb.add_worksheet("Updates Log")
ws3.hide_gridlines(2)
ws3.freeze_panes(2, 0)

U_HDR   = ["#", "Initiative", "Update Note", "Author", "Date"]
U_W     = [4, 34, 66, 20, 14]
U_ALIGN = ["center","left","left","left","center"]

for ci, w in enumerate(U_W):
    ws3.set_column(ci, ci, w)

ws3.merge_range(0, 0, 0, len(U_HDR)-1,
    f"  Progress Updates  ·  {len(updates)} entries",
    F(font_size=14, bold=True, bg_color=NAVY, font_color=WHITE,
      align="left", left=5, left_color="#60A5FA"))
ws3.set_row(0, 30)

for ci, h in enumerate(U_HDR):
    ws3.write(1, ci, h,
        F(bold=True, bg_color=NAVY, font_color=WHITE,
          align=U_ALIGN[ci], indent=1 if U_ALIGN[ci]=="left" else 0,
          border=1, border_color=NAVY2))
ws3.set_row(1, 22)
ws3.autofilter(1, 0, 1, len(U_HDR)-1)

ACCENTS = ["#1B3A6B","#15803D","#B45309","#B91C1C","#1D4ED8","#374151"]
for ri, (uid, iid, init_title, note, author, created_at) in enumerate(updates):
    r  = ri + 2
    bg = STRIPE if ri % 2 == 0 else WHITE
    ac = ACCENTS[ri % len(ACCENTS)]
    ws3.write(r, 0, ri+1,
        F(font_color="#9CA3AF", bg_color=bg, align="center",
          bottom=1, bottom_color=BORDER))
    ws3.write(r, 1, init_title or "",
        F(bold=True, font_color=NAVY2, bg_color=bg, align="left", indent=1,
          bottom=1, bottom_color=BORDER, left=5, left_color=ac))
    ws3.write(r, 2, note or "",
        F(font_color="#0F172A", bg_color=bg, align="left", text_wrap=True,
          bottom=1, bottom_color=BORDER))
    ws3.write(r, 3, author or "",
        F(italic=True, font_color="#475569", bg_color=bg, align="left", indent=1,
          bottom=1, bottom_color=BORDER))
    ws3.write(r, 4, fd(created_at),
        F(font_color="#9CA3AF", bg_color=bg, align="center",
          bottom=1, bottom_color=BORDER))
    ws3.set_row(r, max(20, min(80, (len(note or "") // 60 + 1) * 16)))

# ─── TAB: Initiative Form (hidden) ────────────────────────────────────────────
# A styled input form — VBA shows/hides it; Save calls the API and updates the
# Initiatives sheet in-place.  Columns: A=labels, B=inputs, C=hints, G=state.
wsif = wb.add_worksheet("Initiative Form")
wsif.hide_gridlines(2)
wsif.set_column("A:A", 24)   # labels
wsif.set_column("B:B", 46)   # input cells
wsif.set_column("C:C", 22)   # hints
wsif.set_column("D:F", 2)    # spacer columns
wsif.set_column("G:G", 1)    # off-screen state (mode, id)

IF_HEADER  = F(font_size=15, bold=True, bg_color=NAVY, font_color=WHITE,
               align="left", indent=1, left=5, left_color="#22C55E")
IF_LABEL   = F(bold=True, font_size=10, bg_color="#EFF6FF", font_color=NAVY2,
               align="left", indent=1, border=1, border_color=BORDER)
IF_INPUT   = F(font_size=11, bg_color="#FEFCE8", font_color="#0F172A",
               align="left", indent=1, border=2, border_color="#FDE047")
IF_INPUT_D = F(font_size=11, bg_color="#FEFCE8", font_color="#475569",
               align="left", indent=1, border=2, border_color="#FDE047",
               italic=True)          # description / tall input
IF_HINT    = F(font_size=9, italic=True, bg_color="#F8FAFC", font_color="#94A3B8",
               align="left", indent=1, border=1, border_color=BORDER)
IF_SPACER  = F(bg_color="#F8FAFC")

# Row 0 — header (updated by VBA to show Create vs Edit)
wsif.merge_range(0, 0, 0, 5, "  Create New Initiative", IF_HEADER)
wsif.set_row(0, 40)

# Row 1 — spacer + off-screen state cells (G1=mode, G2=id written by VBA)
wsif.write(1, 0, "", IF_SPACER)
wsif.set_row(1, 8)

# Rows 2–10 — labelled input rows
IF_ROWS = [
    (2,  "Title *",         "B3",  IF_INPUT,   "(required)"),
    (3,  "Status *",        "B4",  IF_INPUT,   "choose from list"),
    (4,  "Priority *",      "B5",  IF_INPUT,   "choose from list"),
    (5,  "Progress (0–100)","B6",  IF_INPUT,   "enter a number"),
    (6,  "Owner",           "B7",  IF_INPUT,   "(optional)"),
    (7,  "Department",      "B8",  IF_INPUT,   "(optional)"),
    (8,  "Description",     "B9",  IF_INPUT_D, "(optional)"),
    (9,  "Start Date",      "B10", IF_INPUT,   "YYYY-MM-DD"),
    (10, "End Date",        "B11", IF_INPUT,   "YYYY-MM-DD"),
]
for row_idx, label, _cell, inp_fmt, hint in IF_ROWS:
    h = 56 if row_idx == 8 else 28
    wsif.write(row_idx, 0, f"  {label}", IF_LABEL)
    wsif.write(row_idx, 1, "", inp_fmt)
    wsif.write(row_idx, 2, hint, IF_HINT)
    wsif.set_row(row_idx, h)

# Row 11 — spacer before buttons
wsif.write(11, 0, "", IF_SPACER); wsif.set_row(11, 10)

# Row 12 — buttons row (actual buttons added by CreateButtons VBA macro)
wsif.write(12, 0, "  Click Save to submit or Cancel to go back.",
    F(italic=True, font_size=9, font_color="#94A3B8", bg_color="#F8FAFC"))
wsif.set_row(12, 36)

# Data validation: Status dropdown
wsif.data_validation(3, 1, 3, 1, {
    "validate": "list",
    "source": ["On Track", "At Risk", "Delayed", "Completed", "Not Started"],
    "dropdown": True,
    "error_message": "Select a status from the dropdown.",
})
# Data validation: Priority dropdown
wsif.data_validation(4, 1, 4, 1, {
    "validate": "list",
    "source": ["High", "Medium", "Low"],
    "dropdown": True,
    "error_message": "Select High, Medium, or Low.",
})
# Data validation: Progress 0-100
wsif.data_validation(5, 1, 5, 1, {
    "validate": "integer",
    "criteria": "between",
    "minimum": 0,
    "maximum": 100,
    "error_message": "Enter a whole number between 0 and 100.",
})

wsif.hide()   # VBA shows/hides this sheet

# ─── TAB: Update Form (hidden) ────────────────────────────────────────────────
wsuf = wb.add_worksheet("Update Form")
wsuf.hide_gridlines(2)
wsuf.set_column("A:A", 24)
wsuf.set_column("B:B", 60)
wsuf.set_column("C:C", 16)
wsuf.set_column("D:F", 2)
wsuf.set_column("G:G", 1)

UF_HEADER = F(font_size=15, bold=True, bg_color=NAVY, font_color=WHITE,
              align="left", indent=1, left=5, left_color="#60A5FA")
UF_LABEL  = F(bold=True, font_size=10, bg_color="#EFF6FF", font_color=NAVY2,
              align="left", indent=1, border=1, border_color=BORDER)
UF_DISP   = F(font_size=11, italic=True, bg_color="#F1F5F9", font_color="#334155",
              align="left", indent=1, border=1, border_color=BORDER)
UF_INPUT  = F(font_size=11, bg_color="#FEFCE8", font_color="#0F172A",
              align="left", indent=1, border=2, border_color="#FDE047",
              text_wrap=True)

# Row 0 — header
wsuf.merge_range(0, 0, 0, 5, "  Add Progress Update", UF_HEADER)
wsuf.set_row(0, 40)

# Row 1 — spacer
wsuf.write(1, 0, "", F(bg_color="#F8FAFC")); wsuf.set_row(1, 8)

# Row 2 — initiative name (display, read-only; VBA writes the name here)
wsuf.write(2, 0, "  Initiative", UF_LABEL)
wsuf.write(2, 1, "", UF_DISP)
wsuf.write(2, 2, "(read only)", F(font_size=9, italic=True, bg_color="#F8FAFC",
                                   font_color="#94A3B8", align="left", indent=1,
                                   border=1, border_color=BORDER))
wsuf.set_row(2, 28)

# Row 3 — note (tall)
wsuf.write(3, 0, "  Note *", UF_LABEL)
wsuf.write(3, 1, "", UF_INPUT)
wsuf.write(3, 2, "(required)", F(font_size=9, italic=True, bg_color="#F8FAFC",
                                  font_color="#94A3B8", align="left", indent=1,
                                  border=1, border_color=BORDER))
wsuf.set_row(3, 80)

# Row 4 — spacer
wsuf.write(4, 0, "", F(bg_color="#F8FAFC")); wsuf.set_row(4, 10)

# Row 5 — author
wsuf.write(5, 0, "  Your Name *", UF_LABEL)
wsuf.write(5, 1, "", UF_INPUT)
wsuf.write(5, 2, "(pre-filled)", F(font_size=9, italic=True, bg_color="#F8FAFC",
                                    font_color="#94A3B8", align="left", indent=1,
                                    border=1, border_color=BORDER))
wsuf.set_row(5, 28)

# Row 6 — spacer
wsuf.write(6, 0, "", F(bg_color="#F8FAFC")); wsuf.set_row(6, 10)

# Row 7 — buttons row (buttons added by CreateButtons VBA)
wsuf.write(7, 0, "  Click Post Update to submit or Cancel to go back.",
    F(italic=True, font_size=9, font_color="#94A3B8", bg_color="#F8FAFC"))
wsuf.set_row(7, 36)

wsuf.hide()   # VBA shows/hides this sheet

wb.close()

# ─── Write VBA macro module (.bas) ────────────────────────────────────────────
with open(BAS_OUT, "w", encoding="utf-8") as f:
    f.write(VBA_CODE.strip() + "\n")

# ─── Zip both files ───────────────────────────────────────────────────────────
import zipfile as _zf

ZIP_OUT = "/home/runner/workspace/initiative_tracker_export.zip"
with _zf.ZipFile(ZIP_OUT, "w", _zf.ZIP_DEFLATED) as z:
    z.write(OUT,     "initiative_tracker.xlsx")
    z.write(BAS_OUT, "initiative_tracker_macros.bas")

import os as _os
print(f"✓  {OUT}")
print(f"   {len(initiatives)} initiatives · {len(updates)} updates")
print(f"✓  {BAS_OUT}")
print(f"✓  {ZIP_OUT}  ({_os.path.getsize(ZIP_OUT):,} bytes)")
