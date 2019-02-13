'' Declare variables for watch folder ''
Dim fso, sourcefolder, folder

Set fso = CreateObject("Scripting.FileSystemObject")
sourcefolder = "C:\Users\r15\Downloads"
Set folder = fso.getfolder(sourcefolder) 

'' Declare variables for Excel workbook '' 
Dim xlFileName, xlApp, xlBook, xlSheet, xlRow

xlFileName = sourcefolder + "\" + "CAT1B_File_Param_test.xlsx"
Set xlApp = CreateObject("Excel.Application")
Set xlBook = xlApp.Workbooks.Open(xlFileName)
Set xlSheet = xlBook.Sheets("DATFiles")

'' Clear all past contents in Excel ''
xlSheet.Range("A2:A100").ClearContents

'' Write all dat files from watch folder into Excel ''
xlApp.DisplayAlerts = False
xlRow = 2
For each file in folder.files
	If lcase(fso.getExtensionName(file.path)) = "dat" then
		xlSheet.Cells(xlRow, 1) = fso.getbasename(file) + ".dat"
		xlRow = xlRow + 1
	End if
Next

'' Save all changes and close Excel workbook ''
xlBook.Save
xlBook.Close SaveChanges=True
Set xlSheet  = Nothing
Set xlBook = Nothing
Set xlApp = Nothing
Set fso = Nothing
Set folder = Nothing