import sys
import time
import subprocess
from pathlib import Path
from subprocess import CompletedProcess

def main():
    args: list = sys.argv[1:]
    encoderPath: Path = None
    sourcePath: Path = None
    distPath: Path = None

    if len(args) == 0 or args[0] == "-h":
        print_help()
        return

    argsResult: (str, str, str) = get_args_values(args)
    if argsResult[1] == None or argsResult[2] == None:
        error("Bad arguments.", True)

    encoderArg = argsResult[0]
    if encoderArg == None:
        encoderArg = try_get_saved_encoder_path()
        if encoderArg == None:
            error("Bad arguments.", True)
    else:
        save_encoder_path(encoderArg)

    encoderPath = Path(encoderArg)
    sourcePath = Path(argsResult[1])
    distPath = Path(argsResult[2])



    check_args_validity(encoderPath, sourcePath, distPath)

    sourceValues = try_get_source_values(sourcePath)

    if len(sourceValues) < 2:
        error("Source file is invalid. Basic requirement is 2 lines: 1 being the id, the other 1 string to encode.")

    if not is_id_line_valid(sourceValues[0]):
        error("First line must be id line and must have this format: id=[4 digit number]." +
            "The 4 digit number should be the mod's nexusmods id with zeroes trailing if necessary.")

    log("Source file is valid.")

    linesToEncode = get_lines_to_encode(sourceValues)
    linesToEncode.insert(0, ";id|key(hex)|key(str)|text")

    log("Creating csv files...")

    createdCsvFiles = create_csv_files(linesToEncode, distPath)

    log("Starting encoder work...")

    encoder_work(encoderPath._str, createdCsvFiles, sourceValues[0][1])

    log("Deleting csv files...")

    delete_files(createdCsvFiles)

    log("Deleting .ws files...")

    delete_files(get_ws_files_from_csv_files(createdCsvFiles))

    log("Renaming .w3strings files...")

    if rename_w3strings(createdCsvFiles):
        log("Done.")
    else:
        log("Finished with errors.")

def encoder_work(encoderPath: str, createdCsvFiles: list, idValue: str):
    commands = []

    for f in createdCsvFiles:
        commands.append("\"" + encoderPath + "\" -e \"" + str(f) + "\" -i " + idValue)

    for c in commands:
        log("Running bash command: " + c, True)
        result: CompletedProcess = subprocess.run(c, stdout=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(" -> Failed")
        else:
            print(" -> Success")

def rename_w3strings(files: list) -> bool:
    success: bool = True

    i: int = 0
    for i in range(len(files)):
        f: Path = files[i]
        f = Path(f._str + ".w3strings")
        lang: str = f.name.split(".")[0]
        newPath: Path = Path(str(f.parent) + "\\" + lang + ".w3strings")

        try:
            f.rename(newPath)
            log("Rename " + f._str + " to " + lang + ".w3strings")
        except FileExistsError:
            f.unlink()
            success = False
            error("A file named \"" + lang + ".w3strings\" was already at destination.", shouldExit=False)

    return success

def get_ws_files_from_csv_files(files: list) -> list:
    wsFiles = []

    i: int = 0
    for i in range(len(files)):
        f: Path = files[i]
        newPath: Path = Path(f._str + ".w3strings.ws")
        wsFiles.append(newPath)

    return wsFiles

def create_csv_files(linesToEncode, destination: Path) -> list:
    langDict: dict = get_lang_meta_dictionary()
    createdFiles = []

    if not destination.exists():
        destination.mkdir()

    for lang in langDict:
        fileToCreate = destination._str + "\\" + lang + "." + str(time.time()) + ".csv"
        p = Path(fileToCreate)
        with p.open(mode="x") as f:
            f.write(";meta[language=" + langDict[lang] + "]\n")
            for line in linesToEncode:
                f.write(line + "\n")

        log("Created " + p.resolve()._str)
        createdFiles.append(p.resolve())

    return createdFiles

def delete_files(fileList: list):
    i: int = 0
    for i in range(len(fileList)):
        p: Path = fileList[i]
        if p.exists():
            p.unlink()
            log("Deleted " + p._str)
        else:
            error("!Critical! Tried to delete file that does not exist.")

def get_lines_to_encode(sourceValues):
    values: list(str) = []

    valueId = int("211" + sourceValues[0][1] + "000")
    for s in sourceValues[1:]:
        values.append(str(valueId) + "||" + s[0] + "|" + s[1])
        valueId += 1

    return values

def try_get_source_values(sourcePath: Path) -> list((str, str)):
    result: list((str, str)) = [];

    with sourcePath.open(mode="r") as source:
        lines: list(str) = source.read().split("\n")

        for line in lines:
            if not line.startswith(";"):
                result.append(get_line_split(line))

    return result

def is_id_line_valid(idLine: (str, str)) -> bool:
    if idLine[0] != "id":
        return False

    idString: str = idLine[1];
    idValue: int

    if len(idString) != 4:
        return False

    try:
        idValue = int(idString)
    except:
        return False

    return True

def get_line_split(value: str, splitArg: str = "=") -> (str, str):
    values: list(str) = value.split(splitArg)

    if len(values) != 2:
        error("Bad source file. Line \"" + value + "\" is bad.")

    return (values[0].strip(), values[1].strip())

def check_args_validity(encoderPath: Path, sourcePath: Path, distPath: Path):
    if not encoderPath.is_file() or encoderPath.name != "w3strings.exe":
        error("encoder path \"" + str(encoderPath) + "\" is bad")

    if not sourcePath.is_file() or sourcePath.suffix != ".txt":
        error("source path \"" + str(sourcePath) + "\" is bad")


def get_args_values(args: list) -> (str, str, str):
    size = len(args)
    encoder: str = None
    source: str = None
    destination: str = None

    i = 0
    for arg in args:
        if arg == "-e" and (i + 1) < size:
            encoder = args[i + 1]
        elif arg == "-s" and (i + 1) < size:
            source = args[i + 1]
        elif arg == "-o" and (i + 1) < size:
            destination = args[i + 1]

        i += 1

    return (encoder, source, destination)

def try_get_saved_encoder_path():
    p: Path = Path("encoder-path.txt")
    result: str

    if not p.is_file():
        return None

    with p.open(mode="r") as value:
        result = value.read()

    log("Read encoder path: " + result)

    return result

def save_encoder_path(line: str):
    with open("encoder-path.txt", mode="w") as f:
        f.write(line)
        log("Saved encoder path.")

def get_lang_meta_dictionary() -> dict:
    return {
        "ar": "cleartext",
        "br": "cleartext",
        "cn": "cleartext",
        "cz": "cz",
        "de": "de",
        "en": "en",
        "es": "es",
        "esMX": "cleartext",
        "fr": "fr",
        "hu": "hu",
        "it": "it",
        "jp": "jp",
        "kr": "cleartext",
        "pl": "pl",
        "ru": "ru",
        "tr": "cleartext",
        "zh": "zh"
    }

def log(msg, hang: bool = False):
    msg = "[Log] " + msg;

    if hang:
        print(msg, end='')
    else:
        print(msg)

def print_help():
    print("#########################################")
    print("#####")
    print("##### w3strings go faster by pMarK")
    print("#####")
    print("##### usage:")
    print("##### -e <encoder path> [only required on first run]")
    print("##### -s <source file path>")
    print("##### -o <output dir path>")
    print("#####")
    print("#########################################")

def error(msg, printHelp: bool = False, shouldExit: bool = True):
    print("[Error] " + msg)

    if printHelp:
        print_help()

    if shouldExit:
        print("[Error] Exiting...")
        exit()

main()