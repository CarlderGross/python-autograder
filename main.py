import subprocess
import os
import re
import shlex
import tempfile
import csv
from tkinter import *

#Constants
SUMMARYTEMPLATE = {
    "Name" : None,
    "Passed" : 0,
    "Failed" : 0,
    "Total" : 0,
    "Flagged" : 0
    }
FLAGPARAMS = ["Name", "Input", "Expected", "Actual"]

def buildTestCases(expectedOutFiles, dataFiles=None):
    #Raises ValueError when it cannot match all inputs to outputs
    #Raises ValueError when it can match some outputs to inputs, but not all
    #Returns a dict if there are both inputs and outputs
    #Returns a list if there are only outputs
    if (dataFiles):
        if (len(expectedOutFiles) == len(dataFiles)):
            finalDict = {}
            for i, datfile in enumerate(dataFiles):
                with open(datfile, 'r') as datFile, open(expectedOutFiles[i], 'r') as outFile:
                    inputLines = datFile.readlines()
                    outputLines = outFile.readlines()
                    if (len(inputLines) == len(outputLines)):
                        for j, in_line in enumerate(inputLines):
                            tup_ins = tuple(shlex.split(in_line)) #use shlex to prevent splitting of string literals with spaces in them
                            tup_outs = tuple(shlex.split(outputLines[j])) #TODO: make sure this makes sense with the output files
                            finalDict[tup_ins] = tup_outs
                    else:
                        raise ValueError(f"Inputs file at index {i} has a different number of test cases than outputs file at that index. Check your file order to make sure they are associated correctly.")
            return finalDict
        else:
            mismatchType = ""
            if (len(expectedOutFiles > len(dataFiles))):
                mismatchType = "some output files have no associated inputs"
            else:
                mismatchType = "some input files have no associated outputs"
            raise ValueError(f"Mismatched number of input and output files: {mismatchType}")
    else:
        outputsList = []
        for file in expectedOutFiles:
            with open(file) as outsFile:
                lines = outsFile.readlines()
                for line in lines:
                    tup_outs = tuple(shlex.split(line)) #TODO: make sure this makes sense with the output files
                    outputsList.append(tup_outs)
        return outputsList

def runPythonTests(filePath, testCases):
    outputs = []
    for inputs in testCases:
        #run the program separately for each test case, since we can't be sure that it will infinitely accept inputs
        inputBuffer = ""
        for item in inputs:
            inputBuffer += str(item)+"\n" #files being tested are probably using input() which requests a string, but stdin expects bytes to be written to it
            #run the subprocess, with stdin as the input stream
        runningFile = subprocess.Popen("py \""+filePath+"\"", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = runningFile.communicate(inputBuffer) #will be a tuple, with the second value as None
        #anything using normal python input (which is most things) will throw EOFError after all test cases have been read; this is probably fine
        outputs.append(output[0])
    return outputs

def inputPromptPattern(file): #parses a python file, and returns a regex pattern to match all string literals passed as the prompt to input() blocks
    inputPrompts = []
    with open(file, 'r') as codeFile:
        for line in codeFile:
            inputIndex = line.find("input(")
            if (inputIndex >= 0):
                p_string = line[inputIndex:]
                endParen = p_string.find(")")
                p_string = p_string[6:endParen]
                if (p_string[0] == "\"" and p_string[-1] == "\""): #if the interior of the input() was a direct string rather than a variable
                    p_string.strip() #strip whitespace
                    p_string = p_string[1:-1] #remove first and last characters (quotation marks)
                    inputPrompts.append(p_string) #we have now identified one of the input prompts
    promptPattern = ""
    for prompt in inputPrompts:
        promptPattern += ""+prompt+"|"
    promptPattern = promptPattern[0:len(promptPattern)-1] #delete the last extraneous separator
    return promptPattern

def runTestsOnAssignment(assignmentPath, testCases):
    summaryLines = []
    flaggedLines = []
    
    with tempfile.TemporaryDirectory() as Temp:
        #Unzip assignment
        subprocess.run("tar -xf "+assignmentPath+" -C "+os.path.abspath(Temp))
        
        for studentFolder in os.scandir(Temp):
            #obtain the student name and initialize the summary dict
            studentName = "".join(studentFolder.name.split(" ", 2)[:2])
            summary = SUMMARYTEMPLATE.copy()
            summary["Name"] = studentName
            summary["Total"] = len(testCases)
            
            #find the most recent revision
            latestRevision = None
            for revisionFolder in os.scandir(studentFolder):
                #second element will always be revision number ("Revision 1 - On time")
                if ((latestRevision == None) or (int(revisionFolder.name.split()[1]) > latestRevision.name.split()[1])):  
                    latestRevision = revisionFolder
            #get the file inside the folder
            pythonFiles = []
            results = None
            for file in os.scandir(latestRevision):
                if (re.match(".*\\.py", file.name)): #must escape backslash to allow it to appear in regex string
                    pythonFiles.append(file)
            if (0 < len(pythonFiles) < 2):
                results = runPythonTests(os.path.abspath(pythonFiles[0]), testCases)
            else:
                for file in pythonFiles:
                    if (re.match("[Mm]ain\\.py")): #preferentially run main.py
                        results = runPythonTests(os.path.abspath(file))
                        break
                    #TODO: also identify projectname.py
                if (not results): #if results is still none, since none is falsey
                    print("Could not identify main file in "+studentFolder.name)
                    print(str(len(pythonFiles))+" python files in "+studentFolder.name+"/"+latestRevision.name)
                    #TODO: add interface to specify which file is desired
    
            promptPattern = inputPromptPattern(file)
            
            for index, result in enumerate(results):
                expectedOut = list(testCases.values())[index]
                #separate hardcoded prompts from actual output
                if (promptPattern):
                    result = re.split(promptPattern, result) #split the string along all known input prompts, leaving only the outputs
                    for i, item in enumerate(result): #clean the results of excess newlines
                        result[i] = item.strip()
                #use tuple comparison to identify passed or failed cases
                tup_result = tuple(result[1:len(expectedOut)+1])
                if (expectedOut == tup_result):
                    summary["Passed"] += 1
                else:
                    if (len(expectedOut) == len(tup_result)):
                        failedElements = len(expectedOut)
                        for i, element in enumerate(expectedOut):
                            if (element in tup_result[i]):
                                failedElements -= 1
                        assert failedElements >= 0
                        if (failedElements == 0):
                            summary["Flagged"] += 1
                            #dump the details of the output to a dict, then add to the list of flagged outputs
                            flaggedOut = dict.fromkeys(FLAGPARAMS)
                            flaggedOut["Name"] = studentName
                            flaggedOut["Input"] = list(testCases.keys())[index]
                            flaggedOut["Expected"] = expectedOut
                            flaggedOut["Actual"] = tup_result
                            flaggedLines.append(flaggedOut)
                    summary["Failed"] += 1
            summaryLines.append(summary)
    
    return(summaryLines, flaggedLines)

def saveToCsv(list_summaryLines, list_flaggedLines):
    #TODO: make a new csv file each time the program is run
    with open("summary.csv", "w", newline="") as summaryFile:
        summaryWriter = csv.DictWriter(summaryFile, fieldnames=SUMMARYTEMPLATE.keys())
        summaryWriter.writeheader()
        for line in list_summaryLines:
            summaryWriter.writerow(line)
    with open("flagged.csv", "w", newline="") as flagsFile:
        flagWriter = csv.DictWriter(flagsFile, fieldnames=FLAGPARAMS)
        flagWriter.writeheader()
        currentName = list_flaggedLines[0]["Name"]
        for line in list_flaggedLines:
            flagWriter.writerow(line)
            if (line["Name"] != currentName): #separate students with empty rows for readability
                flagWriter.writerow(dict.fromkeys(FLAGPARAMS))
                currentName = line["Name"]
    
root = Tk()
root.title("Python Autograder")
main_frame = ttk.frame(root, padding="3 3 12 12")
main_frame.grid(column=0, row=0, sticky=(N, E, S, W))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

assignmentPath = StringVar()

assignmentPath_label = ttk.Label(main_frame, text="Assignment File:")
assignmentPath_entry = ttk.Entry(main_frame, width=20, textvariable=assignmentPath)
assignmentPath_browse = ttk.Button(main_frame, text="Browse...", command=lambda *args : assignmentPath.set(filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")]))) #uses lambda because a button passes miscellaneous args that we aren't using

assignmentPath_label.grid(column=0, row=0, sticky=(N, W))
assignmentPath_entry.grid(column=1, row=0, sticky=(N, W))
assignmentPath_browse.grid(column=2, row=0, sticky=(N, W))

#TODO: actually read test cases from file
tests = { #input : expected output, stored as tuples because there may be more than one
    (1,) : ("2",),
    (2,) : ("3",),
    (5,) : ("6",),
    (7,) : ("8",)
    }

summary, flagged = runTestsOnAssignment(assignmentPath, tests) #decompose the returned tuple
saveToCsv(summary, flagged)