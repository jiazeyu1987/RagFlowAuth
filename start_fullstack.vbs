Dim shell
Dim fso
Dim scriptPath
Dim cmd
Dim i
Dim arg

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "scripts\start_fullstack.ps1")
cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """"

For i = 0 To WScript.Arguments.Count - 1
  arg = WScript.Arguments(i)
  arg = Replace(arg, """", """""")
  cmd = cmd & " """ & arg & """"
Next

shell.Run cmd, 0, False
