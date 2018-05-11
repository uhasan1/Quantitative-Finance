# Import Python Libraries 
import survey

# Import dataset
table = survey.Pregnancies()
table.ReadRecords()
print ("Number of pregnancies is", len(table.records))

# Calculate the descriptive statistics of babies that are live births
liveBirths = 0
firstBirths = 0
notFirstBirths = 0
firstDuration = 0
notFirstDuration = 0
for babies in table.records:
    if babies.outcome == 1:
        liveBirths += 1
        if babies.birthord == 1:
            firstBirths += 1
            firstDuration = firstDuration + babies.prglength
        else:
            notFirstBirths += 1
            notFirstDuration = notFirstDuration + babies.prglength
            
print ("Number of livebirth babies is", liveBirths)
print ("Number of livebirth babies that are first born is", firstBirths)
print ("Number of livebirth babies that are not first born is", notFirstBirths)
print ("Average pregnancy length of livebirth babies that are first born is", firstDuration/firstBirths)
print ("Average pregnancy length of livebirth babies that are not first born is", notFirstDuration/notFirstBirths)
print ("Difference is", firstDuration/firstBirths - notFirstDuration/notFirstBirths, "weeks or", 
       24 * 7 * (firstDuration/firstBirths - notFirstDuration/notFirstBirths), "hours")