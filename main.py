import subprocess
import os

assignmentPath = "FacsimileAssignment.zip"

if (not os.path.exists("Temp")):
    os.mkdir("Temp") #make the temp folder, if it doesn't exist already
    #this folder will be the destination of extracted files from the assignment

#unzip assignment into temp folder
subprocess.run("tar -xf "+assignmentPath+" -C Temp")

#TODO: REPLACE PSEUDOCODE
for studentFolder in os.scandir("Temp"):
    print(studentFolder)
    latestRevision = None
    for revisionFolder in os.scandir(studentFolder):
        pass
    #find the most recent revision
    #run the file inside that folder
    #compare output with test case files
#create csv with results

#TODO: empty the temp folder after use