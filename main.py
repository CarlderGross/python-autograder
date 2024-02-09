import subprocess
import os
import tempfile
from pathlib import Path
import re
import shlex
import csv
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import traceback
import datetime

#Constants
SUMMARYTEMPLATE = {
    "Name" : None,
    "Passed" : 0,
    "Failed" : 0,
    "Total" : 0,
    "Flagged" : 0
    }
FLAGPARAMS = ["Name", "Input", "Expected", "Actual"]

#set up logging
import logging #apparently it works better here?
if(not os.path.isdir("logs")):
    os.mkdir("logs")
logging.basicConfig(filename="logs/latest.log", filemode="w", level=logging.DEBUG, format="%(levelname)s:%(message)s", force=True)

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
                        raise ValueError(f"Inputs file at index {i} has a different number of test cases than associated outputs file. Check your file order to make sure they are associated correctly.")
            return finalDict
        else:
            mismatchType = ""
            if (len(expectedOutFiles) > len(dataFiles)):
                mismatchType = "some output files have no associated inputs!"
            else:
                mismatchType = "some input files have no associated outputs!"
            raise ValueError(mismatchType)
    else:
        outputsList = []
        for file in expectedOutFiles:
            with open(file) as outsFile:
                lines = outsFile.readlines()
                for line in lines:
                    tup_outs = tuple(shlex.split(line)) #TODO: make sure this makes sense with the output files
                    outputsList.append(tup_outs)
        return outputsList

def runPythonTests(filePath, testInputs=None):
    outputs = []
    if (testInputs):
        for inputs in testInputs:
            #run the program separately for each test case, since we can't be sure that it will infinitely accept inputs
            inputBuffer = ""
            for item in inputs:
                inputBuffer += str(item)+"\n" #files being tested are probably using input() which requests a string, but stdin expects bytes to be written to it
                #run the subprocess, with stdin as the input stream
            runningFile = subprocess.Popen("py \""+filePath+"\"", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output = runningFile.communicate(inputBuffer) #will be a tuple, with the second value as None
            #anything using normal python input (which is most things) will throw EOFError after all test cases have been read; this is probably fine
            runningFile.terminate()
            outputs.append(output[0])
    else:
        output_process = subprocess.run("py \""+filePath+"\"", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=100)
        outputs = output_process.stdout.split("\n") #the outputs are actually the singular output split by line
    logging.debug(outputs)
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

def findPythonFiles(folder):
    pythonFiles = []
    zips = []
    for file in os.scandir(folder):
        if (re.match(".*\\.py", file.name)): #must escape backslash to allow it to appear in regex string
            pythonFiles.append(file)
        elif (re.match(".*\\.zip", file.name)):
            zips.append(file)
    if (len(pythonFiles) == 0) and (len(zips) == 1):
        logging.warning("No python file found in "+folder+", attempting to unzip detected zip file")
        zipname = Path(os.path.abspath(zips[0])).stem() #get the basic name of the zip, which will be the new folder
        newFolder = os.path.join(folder, zipname)
        subprocess.run("tar -xf \""+os.path.abspath(zips[0])+"\" -C "+newFolder) #unzip
        assert os.path.isdir(newFolder) #debug
        findPythonFiles(newFolder) #recursively find files in the new folder
    return pythonFiles

def runTestsOnAssignment(assignmentPath, testCases):
    summaryLines = []
    flaggedLines = []
    
    with tempfile.TemporaryDirectory() as Temp:
        #Unzip assignment
        subprocess.run("tar -xf \""+assignmentPath+"\" -C "+os.path.abspath(Temp))
        
        for studentFolder in os.scandir(Temp):
            logging.info("Testing "+os.path.abspath(studentFolder))
            #obtain the student name and initialize the summary dict
            studentName = "".join(studentFolder.name.split(" ", 2)[:2])
            summary = SUMMARYTEMPLATE.copy()
            summary["Name"] = studentName
            summary["Total"] = len(testCases)
            
            #find the most recent revision
            latestRevision = None
            for revisionFolder in os.scandir(studentFolder):
                #second element will always be revision number ("Revision 1 - On time")
                if ((latestRevision == None) or (int(revisionFolder.name.split()[1]) > int(latestRevision.name.split()[1]))):  
                    latestRevision = revisionFolder
            #get the file inside the folder
            pythonFiles = findPythonFiles(latestRevision)
            targetFile = None
            #figure out what file to run
            if (0 < len(pythonFiles) < 2):
                #if there's only one file, use that
                targetFile = pythonFiles[0]
            else:
                for file in pythonFiles:
                    if (re.match("[Mm]ain\\.py")): #preferentially run main.py
                        targetFile = file
                        break
                        #TODO: also identify projectname.py
                if (not targetFile): #if no file was identified as main
                    logging.error("Could not identify main file in "+studentFolder.name)
                    logging.error(str(len(pythonFiles))+" python files in "+studentFolder.name+"/"+latestRevision.name)
                    break #TODO: add interface to specify which file is desired
                        
            promptPattern = inputPromptPattern(targetFile)
            
            if (isinstance(testCases, dict)):
                expectedResults = list(testCases.values())
                results = runPythonTests(os.path.abspath(targetFile), testInputs=list(testCases.keys()))
            else:
                assert isinstance(testCases, list)
                expectedResults = testCases
                results = runPythonTests(os.path.abspath(targetFile))
            
            for index, expectedOut in enumerate(expectedResults):
                try:
                    result = results[index]
                except IndexError:
                    logging.info("Fail: No output provided")
                    summary["Failed"] += 1
                else:
                    logging.debug(result)
                    #separate hardcoded prompts from actual output
                    if (promptPattern):
                        result = re.split(promptPattern, result) #split the string along all known input prompts, leaving only the outputs
                    else:
                        #"split" the string into nothing and itself
                        #regex split with no pattern actually splits it into one string per letter, plus an empty string at the beginning and end, which we don't want
                        fakesplit = [""]
                        fakesplit.append(result)
                        result = fakesplit
                    
                    logging.debug(result)
                    for i, item in enumerate(result): #clean the results of excess newlines
                        result[i] = item.strip()
                    
                    #use tuple comparison to identify passed or failed cases
                    logging.debug(result)
                    logging.debug("Pre-tuple result: "+str(result[1:len(expectedOut)+1]))
                    tup_result = tuple(result[1:len(expectedOut)+1])
                    logging.debug("Expected: " + str(expectedOut))
                    logging.debug("Received: " + str(tup_result))
                    if (expectedOut == tup_result):
                        logging.debug("Pass")
                        summary["Passed"] += 1
                    else:
                        if (len(expectedOut) == len(tup_result)):
                            failedElements = len(expectedOut)
                            for i, element in enumerate(expectedOut):
                                if (element in tup_result[i]):
                                    failedElements -= 1
                            assert failedElements >= 0
                            if (failedElements == 0):
                                logging.debug("Flag")
                                summary["Flagged"] += 1
                                #dump the details of the output to a dict, then add to the list of flagged outputs
                                flaggedOut = dict.fromkeys(FLAGPARAMS)
                                flaggedOut["Name"] = studentName
                                flaggedOut["Input"] = list(testCases.keys())[index]
                                flaggedOut["Expected"] = expectedOut
                                flaggedOut["Actual"] = tup_result
                                flaggedLines.append(flaggedOut)
                        logging.debug("Fail")
                        summary["Failed"] += 1
            summaryLines.append(summary)
    
    return(summaryLines, flaggedLines)

def saveToCsv(list_summaryLines, list_flaggedLines, assignmentname):
    savedir = assignmentname+" "+datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S")
    os.mkdir(savedir)
    with open(savedir+"/summary.csv", "w", newline="") as summaryFile:
        summaryWriter = csv.DictWriter(summaryFile, fieldnames=SUMMARYTEMPLATE.keys())
        summaryWriter.writeheader()
        for line in list_summaryLines:
            summaryWriter.writerow(line)
    if (list_flaggedLines):
        with open(savedir+"/flagged.csv", "w", newline="") as flagsFile:
            flagWriter = csv.DictWriter(flagsFile, fieldnames=FLAGPARAMS)
            flagWriter.writeheader()
            currentName = list_flaggedLines[0]["Name"]
            for line in list_flaggedLines:
                flagWriter.writerow(line)
                if (line["Name"] != currentName): #use empty rows to separate students for readability
                    flagWriter.writerow(dict.fromkeys(FLAGPARAMS))
                    currentName = line["Name"]

#construct interface
root = Tk()
root.title("Python Autograder")
main_frame = ttk.Frame(root, padding="3 3 12 12")
main_frame.grid(column=0, row=0, sticky=(N, E, S, W))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

assignment_frame = ttk.Frame(main_frame)
assignment_frame.grid(column=0, row=0, sticky=(N, W))

assignmentPath = StringVar()
assignmentPath_label = ttk.Label(assignment_frame, text="Assignment File:")
assignmentPath_entry = ttk.Entry(assignment_frame, width=100, textvariable=assignmentPath)
assignmentPath_browse = ttk.Button(assignment_frame, text="Browse...", command=lambda: assignmentPath.set(filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")]))) #uses lambda because a button passes miscellaneous args that we aren't using

assignmentPath_label.grid(column=0, row=0, sticky=(N, W))
assignmentPath_entry.grid(column=0, row=1, sticky=(N, W, E))
assignmentPath_browse.grid(column=1, row=1, sticky=(N, W))

inputFiles = []
outputFiles= []

filelist_frame = ttk.Frame(main_frame)
filelist_frame.columnconfigure((0, 1), weight=1, uniform="column")
filelist_frame.grid(column=0, row=1, sticky=(N, W, S, E))

indata_label = ttk.Label(filelist_frame, text="Input Datafiles:")
outdata_label = ttk.Label(filelist_frame, text="Output Datafiles:")

indata_label.grid(column=0, row=0, sticky=(N, W))
outdata_label.grid(column=1, row=0, sticky=(N, W))

inlist_frame = ttk.Frame(filelist_frame)
inlist_frame.grid(column=0, row=1, sticky=(N, W, S, E))
outlist_frame = ttk.Frame(filelist_frame)
outlist_frame.grid(column=1, row=1, sticky=(N, W, S, E))

#interface functions
def redrawInputFiles():
    for child in inlist_frame.winfo_children():
        child.grid_forget()
        child.destroy()
    for index, element in enumerate(inputFiles):
        elementLabel = ttk.Label(inlist_frame, text=os.path.abspath(element))
        elementLabel.grid(column=0, row=index+1, sticky=(W))
        removalButton = ttk.Button(inlist_frame, text="X", width=1.1, command=lambda: removeInputFile(index))
        removalButton.grid(column=1, row=index+1, sticky=W)
        
def redrawOutputFiles():
    for child in outlist_frame.winfo_children():
        child.grid_forget()
        child.destroy()
    for index, element in enumerate(outputFiles):
        elementLabel = ttk.Label(outlist_frame, text=os.path.abspath(element))
        elementLabel.grid(column=0, row=index+1, sticky=(N, W))
        removalButton = ttk.Button(outlist_frame, text="X", width=1.1, command=lambda: removeOutputFile(index))
        removalButton.grid(column=1, row=index+1, sticky=W)
        
#whenever the list changes, we need to redraw it
def addInputFiles(*args): #must include arbitrary args and then ignore them, because a button passes args to the called function
    global inputFiles #can't return anything because this will occur inside a button
    inputFiles += filedialog.askopenfilenames(filetypes=[("Data files", "*.dat")])
    redrawInputFiles()
    
def addOutputFiles(*args):
    global outputFiles
    outputFiles += filedialog.askopenfilenames(filetypes=[("Text files", "*.txt")])
    redrawOutputFiles()
    
def removeInputFile(index):
    del inputFiles[index]
    redrawInputFiles()
    
def removeOutputFile(index):
    del outputFiles[index]
    redrawOutputFiles()

indata_browse = ttk.Button(filelist_frame, text="Browse...", command=addInputFiles)
outdata_browse = ttk.Button(filelist_frame, text="Browse...", command=addOutputFiles)

indata_browse.grid(column=0, row=2, sticky=(N, W))
outdata_browse.grid(column=1, row=2, sticky=(N, W))

assoc_warning_label = ttk.Label(main_frame, text="Make sure each input file is associated with an output file!")
assoc_warning_label.grid(column=0, row=2, sticky=(N, W), columnspan=2)

def runTestsCallback(*args):
    global inputFiles, outputFiles
    logging.info("Attempting to run tests on "+assignmentPath.get())
    if (not assignmentPath.get()):
        logging.error("Cannot run tests: no assignment file selected!")
        messagebox.showinfo(parent=root, title="Error", message="Cannot run tests: no assignment file selected!")
        return -1
    if (not outputFiles):
        logging.error("Cannot run tests: no expected output files provided!")
        messagebox.showinfo(parent=root, title="Error", message="Cannot run tests: no expected output files provided!")
        return -1
    try:
        tests = buildTestCases(outputFiles, dataFiles=inputFiles)
    except ValueError as e:
        logging.error("Cannot run tests: "+str(e))
        messagebox.showinfo(parent=root, title="Error", message="Cannot run tests: "+str(e))
    else:
        logging.debug("Running tests...")
        try:
            summary, flagged = runTestsOnAssignment(assignmentPath.get(), tests)
            saveToCsv(summary, flagged, Path(assignmentPath.get()).stem)
            messagebox.showinfo(parent=root, title="Success", message="Tests run successfully!")
        except Exception as e:
            logging.critical(traceback.format_exc())
            #make sure the user knows what's going on
            messagebox.showinfo(parent=root, title="Error", message="Failed to run tests: "+str(e))
            root.destroy()
            raise

runTests_button = ttk.Button(main_frame, text="Run Tests", default="active", command=runTestsCallback)
runTests_button.grid(column=1, row=2, sticky=(S, E))

root.mainloop()
#copy latest log to dated log after root closes
with open("logs/"+datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S")+".log", mode="a") as permLog, open("logs/latest.log", mode="r") as latestLog:
    for line in latestLog:
        permLog.write(line)