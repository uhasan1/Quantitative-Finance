''Declare all necessary variables
Dim stPath
stPath = "H:\FxGrp\CUM\"

Dim noSession
Dim noDatabase
Dim noView
Dim noDocument
Dim noNextDocument
Dim mailServer
Dim mailFile

Const EMBED_ATTACHMENT = 1454
Const RICHTEXT = 1

''Embedded objects are of the datatype Variant.
Dim vaItem  
Dim vaAttachment 
 
''Instantiate the Notes session.
Set noSession = CreateObject("Notes.NotesSession")
 
''Instantiate the actual Notes database.
mailServer = noSession.GetEnvironmentString("MailServer", True)
mailFile = noSession.GetEnvironmentString("MailFile", True)
Set noDatabase = noSession.GetDatabase(mailServer, mailFile)

''Folders are views in Lotus Notes and in this example the EBS folder is used to store all the NDF reports.
Set noView = noDatabase.GetView("EBS")
noView.AutoUpdate = False
  
''Get the first document in the defined view.
Set noDocument = noView.GetFirstDocument

''Iterate through all the e-mails in the EBS folder.
Dim k
k = 0

Do Until noDocument Is Nothing
Set noNextDocument = noView.GetNextDocument(noDocument)
    ''Check if the document has an attachment or not.
    If noDocument.HasEmbedded Then
      Set vaItem = noDocument.GetFirstItem("Body")
      If vaItem.Type = RICHTEXT Then
        For Each vaAttachment In vaItem.EmbeddedObjects
          If vaAttachment.Type = EMBED_ATTACHMENT Then
            ''Match the current file name against preceding file name
                ''Save attachments into the designated folder
                vaAttachment.ExtractFile stPath & vaAttachment.Name
          End If
        Next
      End If
    End If
    Set noDocument = noNextDocument
Loop

''Release objects from memory.
Set noNextDocument = Nothing
Set noDocument = Nothing
Set noView = Nothing
Set noDatabase = Nothing
Set noSession = Nothing
Set vaItem = Nothing