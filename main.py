import subprocess
import os
import re
import shutil

assignmentPath = "FacsimileAssignment.zip"

#TODO: actually read test cases from file
testCases = { #input : expected output
    1 : 2
    }

#Unzip assignment
if (not os.path.exists("Temp")):
    os.mkdir("Temp") #make the temp folder, if it doesn't exist already
    #this folder will be the destination of extracted files from the assignment
subprocess.run("tar -xf "+assignmentPath+" -C Temp") #unzip assignment into temp

def runPythonFile(filePath):
    outs = []
    print("Running "+filePath)
    runningFile = subprocess.Popen("py \""+filePath+"\"", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for valueIn in testCases:
        result, ignore = runningFile.communicate("1\n")
        #this may close stdin after sending, which is bad
        #try accessing stdin directly instead?
        outs.append(result) #TODO: replace this to actually analyze later
    runningFile.terminate() #when we're out of test cases, we're done
    print(outs)
        

for studentFolder in os.scandir("Temp"):
    #print(studentFolder)
    #find the most recent revision
    latestRevision = None
    for revisionFolder in os.scandir(studentFolder):
        #second element will always be revision number ("Revision 1 - On time")
        if ((latestRevision == None) or (int(revisionFolder.name.split()[1]) > latestRevision.name.split()[1])):  
            latestRevision = revisionFolder
    #get the file inside the folder
    pythonFiles = []
    for file in os.scandir(latestRevision):
        print(file.name)
        if (re.match(".*\\.py", file.name)): #must escape backslash to allow it to appear in regex string
            pythonFiles.append(file)
    if (0 < len(pythonFiles) < 2):
        runPythonFile(os.path.abspath(pythonFiles[0]))
    else:
        print("Could not run project in "+studentFolder.name)
        print(str(len(pythonFiles))+" python files in "+studentFolder.name+"/"+latestRevision.name)
        #TODO: add interface to specify which file is desired
    

shutil.rmtree("Temp")