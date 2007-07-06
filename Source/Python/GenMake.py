#!/usr/bin/env python

"""Create makefile for MS nmake and GNU make"""

import os, sys, string, re
import os.path as path

from SequentialDict import *
from EdkIIWorkspaceBuild import *
from EdkIIWorkspace import *
from BuildInfo import *

gDependencyDatabase = {}    # file path : [dependent files list]
gIncludePattern = re.compile("^[ \t#]*include[ \t]+[\"<]*([^\"<>]+)[>\" \t\n\r]*", re.MULTILINE | re.UNICODE)

class AutoGenString(object):
    def __init__(self):
        self.String = ''

    def __str__(self):
        return self.String

    def Append(self, AppendString, Dictionary=None):
        if Dictionary == None:
            self.String += AppendString
        else:
            while AppendString.find('${BEGIN}') >= 0:
                Start = AppendString.find('${BEGIN}')
                End   = AppendString.find('${END}')
                SubString = AppendString[AppendString.find('${BEGIN}'):AppendString.find('${END}')+6]
                
                RepeatTime = -1
                NewDict = {"BEGIN":"", "END":""}
                for Key in Dictionary:
                    if SubString.find('$' + Key) >= 0 or SubString.find('${' + Key + '}') >= 0:
                        Value = Dictionary[Key]
                        if type(Value) != type([]):
                            NewDict[Key] = Value
                            continue
                        if RepeatTime < 0:
                            RepeatTime = len(Value)
                        elif RepeatTime != len(Value):
                            raise Exception(Key + " has different repeat time from others!")
                        NewDict[Key] = ""

                NewString = ''
                for Index in range(0, RepeatTime):
                    for Key in NewDict:
                        if Key == "BEGIN" or Key == "END" or type(Dictionary[Key]) != type([]):
                            continue
                        #print "###",Key
                        NewDict[Key] = Dictionary[Key][Index]
                    NewString += string.Template(SubString).safe_substitute(NewDict)
                AppendString = AppendString[0:Start] + NewString + AppendString[End + 6:]

            NewDict = {}
            for Key in Dictionary:
                if type(Dictionary[Key]) == type([]):
                    continue
                NewDict[Key] = Dictionary[Key]
            self.String += string.Template(AppendString).safe_substitute(NewDict)


MakefileHeader = '''#
# DO NOT EDIT
# This file is auto-generated by build utility
#
# Module Name:
#
#   %s
#
# Abstract:
#
#   Auto-generated makefile for building module and libraries
#
'''

LibraryMakeCommand = '''cd %(makedir)s
\t$(MAKE) $(MAKE_FLAGS) -f %(makefile)s %(target)s
\tcd $(MODULE_BUILD_DIR)'''

gMakeType = ""
if sys.platform == "win32":
    gMakeType = "nmake"
else:
    gMakeType = "gmake"

gMakefileName = {"nmake" : "Makefile", "gmake" : "GNUmakefile"}

gDirectorySeparator = {"nmake" : "\\", "gmake" : "/"}

OutputFlag = {
    ("MSFT", "CC", "OUTPUT")      :   "/Fo",
    ("MSFT", "SLINK", "OUTPUT")   :   "/OUT:",
    ("MSFT", "DLINK", "OUTPUT")   :   "/OUT:",
    ("MSFT", "ASMLINK", "OUTPUT") :   "/OUT:",
    ("MSFT", "PCH", "OUTPUT")     :   "/Fp",
    ("MSFT", "ASM", "OUTPUT")     :   "/Fo",
    
    ("INTEL", "CC", "OUTPUT")          :   "/Fo",
    ("INTEL", "SLINK", "OUTPUT")       :   "/OUT:",
    ("INTEL", "DLINK", "OUTPUT")       :   "/OUT:",
    ("INTEL", "ASMLINK", "OUTPUT")     :   "/OUT:",
    ("INTEL", "PCH", "OUTPUT")         :   "/Fp",
    ("INTEL", "ASM", "OUTPUT")         :   "/Fo",
    ("INTEL", "IPF", "ASM", "OUTPUT")  :   "-o ",

    ("GCC", "CC", "OUTPUT")        :   "-o ",
    ("GCC", "SLINK", "OUTPUT")     :   "-cr ",
    ("GCC", "DLINK", "OUTPUT")     :   "-o ",
    ("GCC", "ASMLINK", "OUTPUT")   :   "-o ",
    ("GCC", "PCH", "OUTPUT")       :   "-o ",
    ("GCC", "ASM", "OUTPUT")       :   "-o ",

    ("OUTPUT")                     : "-o "
}

IncludeFlag = {"MSFT" : "/I", "GCC" : "-I"}

gCustomMakefileTemplate = '''
${makefile_header}

#
# Platform Macro Definition
#
PLATFORM_NAME = ${platform_name}
PLATFORM_GUID = ${platform_guid}
PLATFORM_VERSION = ${platform_version}
PLATFORM_RELATIVE_DIR = ${platform_relative_directory}
PLATFORM_DIR = $(WORKSPACE)${separator}${platform_relative_directory}
PLATFORM_OUTPUT_DIR = ${platform_output_directory}

#
# Package Macro Definition
#
PACKAGE_NAME = ${package_name}
PACKAGE_GUID = ${package_guid}
PACKAGE_VERSION = ${package_version}
PACKAGE_RELATIVE_DIR = ${package_relative_directory}
PACKAGE_DIR = $(WORKSPACE)${separator}${package_relative_directory}

#
# Module Macro Definition
#
MODULE_NAME = ${module_name}
MODULE_GUID = ${module_guid}
MODULE_VERSION = ${module_version}
MODULE_TYPE = ${module_type}
MODULE_FILE_BASE_NAME = ${module_file_base_name}
BASE_NAME = $(MODULE_NAME)
MODULE_RELATIVE_DIR = ${module_relative_directory}
MODULE_DIR = $(WORKSPACE)${separator}${module_relative_directory}

#
# Build Configuration Macro Definition
#
ARCH = ${architecture}
TOOLCHAIN_TAG = ${toolchain_tag}
TARGET = ${build_target}

#
# Build Directory Macro Definition
#
PLATFORM_BUILD_DIR = ${platform_build_directory}
BUILD_DIR = ${platform_build_directory}${separator}${build_target}_${toolchain_tag}
BIN_DIR = $(BUILD_DIR)${separator}${architecture}
LIB_DIR = $(BIN_DIR)
MODULE_BUILD_DIR = $(BUILD_DIR)${separator}${architecture}${separator}${module_relative_directory}${separator}${module_file_base_name}
OUTPUT_DIR = $(MODULE_BUILD_DIR)${separator}OUTPUT
DEBUG_DIR = $(MODULE_BUILD_DIR)${separator}DEBUG
DEST_DIR_OUTPUT = $(OUTPUT_DIR)
DEST_DIR_DEBUG = $(DEBUG_DIR)

#
# Default Tools Flags Macro Definition (from tools_def.txt by default)
#
${BEGIN}DEFAULT_${tool_code}_FLAGS = ${default_tool_flags}
${END}

#
# Platform Tools Flags Macro Definition (from platform description file)
#
${BEGIN}PLATFORM_${tool_code}_FLAGS = ${platform_tool_flags}
${END}

#
# Platform Tools Flags Macro Definition (from platform description file)
#
${BEGIN}MODULE_${tool_code}_FLAGS = ${module_tool_flags}
${END}

#
# ToolsFlagMacro
#
${BEGIN}${tool_code}_FLAGS = $(DEFAULT_${tool_code}_FLAGS) $(PLATFORM_${tool_code}_FLAGS) $(MODULE_${tool_code}_FLAGS)
${END}
MAKE_FLAGS = /nologo

#
# ToolsPathMacro
#
${BEGIN}${tool_code} = ${tool_path}
${END}

${custom_makefile_content}

#
# Target used when called from platform makefile, which will bypass the build of dependent libraries
#

pbuild: init all


#
# Target used for library build, which will bypass the build of dependent libraries
#

lbuild: init all


#
# ModuleTarget
#

mbuild: init all


#
# Initialization target: print build information and create necessary directories
#
init:
\t-@echo Building ... $(MODULE_NAME)-$(MODULE_VERSION) [$(ARCH)] in package $(PACKAGE_NAME)-$(PACKAGE_VERSION)
\t${create_directory_command} $(DEBUG_DIR) > NUL 2>&1
\t${create_directory_command} $(OUTPUT_DIR) > NUL 2>&1
\t${BEGIN}${create_directory_command} $(OUTPUT_DIR)${separator}${directory_to_be_created} > NUL 2>&1
\t${END}

'''

gModuleMakefileTemplate = '''
${makefile_header}

#
# Platform Macro Definition
#
PLATFORM_NAME = ${platform_name}
PLATFORM_GUID = ${platform_guid}
PLATFORM_VERSION = ${platform_version}
PLATFORM_RELATIVE_DIR = ${platform_relative_directory}
PLATFORM_DIR = $(WORKSPACE)${separator}${platform_relative_directory}
PLATFORM_OUTPUT_DIR = ${platform_output_directory}

#
# Package Macro Definition
#
PACKAGE_NAME = ${package_name}
PACKAGE_GUID = ${package_guid}
PACKAGE_VERSION = ${package_version}
PACKAGE_RELATIVE_DIR = ${package_relative_directory}
PACKAGE_DIR = $(WORKSPACE)${separator}${package_relative_directory}

#
# Module Macro Definition
#
MODULE_NAME = ${module_name}
MODULE_GUID = ${module_guid}
MODULE_VERSION = ${module_version}
MODULE_TYPE = ${module_type}
MODULE_FILE_BASE_NAME = ${module_file_base_name}
BASE_NAME = $(MODULE_NAME)
MODULE_RELATIVE_DIR = ${module_relative_directory}
MODULE_DIR = $(WORKSPACE)${separator}${module_relative_directory}

#
# Build Configuration Macro Definition
#
ARCH = ${architecture}
TOOLCHAIN_TAG = ${toolchain_tag}
TARGET = ${build_target}

#
# Build Directory Macro Definition
#
PLATFORM_BUILD_DIR = ${platform_build_directory}
BUILD_DIR = ${platform_build_directory}${separator}${build_target}_${toolchain_tag}
BIN_DIR = $(BUILD_DIR)${separator}${architecture}
LIB_DIR = $(BIN_DIR)
MODULE_BUILD_DIR = $(BUILD_DIR)${separator}${architecture}${separator}${module_relative_directory}${separator}${module_file_base_name}
OUTPUT_DIR = $(MODULE_BUILD_DIR)${separator}OUTPUT
DEBUG_DIR = $(MODULE_BUILD_DIR)${separator}DEBUG
DEST_DIR_OUTPUT = $(OUTPUT_DIR)
DEST_DIR_DEBUG = $(DEBUG_DIR)

#
# Default Tools Flags Macro Definition (from tools_def.txt by default)
#
${BEGIN}DEFAULT_${tool_code}_FLAGS = ${default_tool_flags}
${END}

#
# Platform Tools Flags Macro Definition (from platform description file)
#
${BEGIN}PLATFORM_${tool_code}_FLAGS = ${platform_tool_flags}
${END}

#
# Module Tools Flags Macro Definition (from platform/module description file)
#
${BEGIN}MODULE_${tool_code}_FLAGS = ${module_tool_flags}
${END}

#
# Tools Flag Macro
#
${BEGIN}${tool_code}_FLAGS = $(DEFAULT_${tool_code}_FLAGS) $(PLATFORM_${tool_code}_FLAGS) $(MODULE_${tool_code}_FLAGS)
${END}
MAKE_FLAGS = /nologo

#
# Tools Path Macro
#
${BEGIN}${tool_code} = ${tool_path}
${END}

#
# Build Macro
#
SOURCE_FILES = ${BEGIN}$(MODULE_DIR)${separator}${source_file} \\
               ${END}${BEGIN}$(DEBUG_DIR)${separator}${auto_generated_file}
               ${END}

INC = ${BEGIN}${include_path_prefix}$(WORKSPACE)${separator}${include_path} \\
      ${END}

OBJECTS = ${BEGIN}$(OUTPUT_DIR)${separator}${object_file} \\
          ${END}

LIBS = ${BEGIN}$(LIB_DIR)${separator}${library_file} \\
       ${END}

COMMON_DEPS = ${BEGIN}$(WORKSPACE)${separator}${common_dependency_file} \\
              ${END}

ENTRYPOINT = ${module_entry_point}

#
# Target File Macro Definitions
#
PCH_FILE = $(OUTPUT_DIR)\$(MODULE_NAME).pch
LIB_FILE = $(LIB_DIR)\$(MODULE_NAME).lib
LLIB_FILE = $(OUTPUT_DIR)\$(MODULE_NAME)Local.lib
DLL_FILE = $(DEBUG_DIR)\$(MODULE_NAME).dll
EFI_FILE = $(OUTPUT_DIR)\$(MODULE_NAME).efi

#
# Overridable Target Macro Definitions
#
INIT_TARGET = init
PCH_TARGET =
LLIB_TARGET = $(LLIB_FILE)

#
# Default target, which will build dependent libraries in addition to source files
#

all: ${build_type}


#
# Target used when called from platform makefile, which will bypass the build of dependent libraries
#

pbuild: $(INIT_TARGET) $(PCH_TARGET) gen_obj $(LLIB_TARGET) $(EFI_FILE) $(DLL_FILE)


#
# Target used for library build, which will bypass the build of dependent libraries
#

lbuild: $(INIT_TARGET) $(PCH_TARGET) gen_obj $(LIB_FILE)


#
# ModuleTarget
#

mbuild: $(INIT_TARGET) gen_libs $(PCH_TARGET) gen_obj $(LLIB_TARGET) $(EFI_FILE) $(DLL_FILE)


#
# Initialization target: print build information and create necessary directories
#
init:
\t-@echo Building ... $(MODULE_NAME)-$(MODULE_VERSION) [$(ARCH)] in package $(PACKAGE_NAME)-$(PACKAGE_VERSION)
\t${create_directory_command} $(DEBUG_DIR) > NUL 2>&1
\t${create_directory_command} $(OUTPUT_DIR) > NUL 2>&1
\t${BEGIN}${create_directory_command} $(OUTPUT_DIR)${separator}${directory_to_be_created} > NUL 2>&1
\t${END}

#
# PCH Target
#
pch: $(PCH_FILE)


#
# Libs Target
#
libs: gen_libs


#
# Vfr Target
#
vfr: gen_vfr


#
# Obj Target
#
obj: $(PCH_TARGET) gen_obj


#
# LocalLib Target
#
locallib: $(PCH_TARGET) gen_obj $(LLIB_FILE)


#
# Dll Target
#
dll: gen_libs $(PCH_TARGET) gen_obj $(LLIB_TARGET) $(DLL_FILE)


#
# Efi Target
#
efi: gen_libs $(PCH_TARGET) gen_obj $(LLIB_TARGET) $(DLL_FILE) $(EFI_FILE)


#
# GenLibsTarget
#
gen_libs:
\t${BEGIN}cd $(BUILD_DIR)${separator}$(ARCH)${separator}${dependent_library_build_directory}
\t$(MAKE) $(MAKE_FLAGS)
\t${END}cd $(MODULE_BUILD_DIR)

#
# GenVfrTarget
#

gen_vfr:
\t@echo placeholder: processing vfr files

#
# Phony targets for objects
#

gen_obj: $(PCH_TARGET) $(OBJECTS)


#
# PCH file build target
#

$(PCH_FILE): $(DEP_FILES)
\t$(PCH) $(CC_FLAGS) $(PCH_FLAGS) $(DEP_FILES)

#
# Local Lib file build target
#

$(LLIB_FILE): $(OBJECTS)
\t"$(SLINK)" $(SLINK_FLAGS) /OUT:$(LLIB_FILE) $(OBJECTS)

#
# Library file build target
#

$(LIB_FILE): $(OBJECTS)
\t"$(SLINK)" $(SLINK_FLAGS) /OUT:$(LIB_FILE) $(OBJECTS)

#
# DLL file build target
#

$(DLL_FILE): $(LIBS) $(LLIB_FILE)
\t"$(DLINK)" $(DLINK_FLAGS) /OUT:$(DLL_FILE) $(DLINK_SPATH) $(LIBS) $(LLIB_FILE)

#
# EFI file build target
#

$(EFI_FILE): $(LIBS) $(LLIB_FILE)
\t"$(DLINK)" $(DLINK_FLAGS) /OUT:$(EFI_FILE) $(DLINK_SPATH) $(LIBS) $(LLIB_FILE)
\tGenFw -e ${module_type} -o $(EFI_FILE) $(EFI_FILE)
\tcopy /y $(EFI_FILE) $(BIN_DIR)

#
# Individual Object Build Targets
#
${BEGIN}${object_build_target}
${END}


#
# clean all intermediate files
#

clean:
\t- @rmdir /s /q $(OUTPUT_DIR) > NUL 2>&1

#
# clean all generated files
#

cleanall:
\t- @rmdir /s /q $(OUTPUT_DIR) $(DEBUG_DIR) > NUL 2>&1
\t- @del /f /q *.pdb *.idb > NUL 2>&1

#
# clean pre-compiled header files
#

cleanpch:
\t- @del /f /q $(OUTPUT_DIR)\*.pch > NUL 2>&1

#
# clean all dependent libraries built
#

cleanlib:
\t@echo clean all dependent libraries built

'''

gPlatformMakefileTemplate = '''
${makefile_header}

#
# Platform Macro Definition
#
PLATFORM_NAME = ${platform_name}
PLATFORM_GUID = ${platform_guid}
PLATFORM_VERSION = ${platform_version}
PLATFORM_DIR = $(WORKSPACE)${separator}${platform_relative_directory}
PLATFORM_OUTPUT_DIR = ${platform_output_directory}

#
# Build Configuration Macro Definition
#
TOOLCHAIN_TAG = ${toolchain_tag}
TARGET = ${build_target}
MAKE_FLAGS = /nologo

#
# Build Directory Macro Definition
#
BUILD_DIR = ${platform_build_directory}${separator}${build_target}_${toolchain_tag}
FV_DIR = ${platform_build_directory}${separator}${build_target}_${toolchain_tag}${separator}FV

#
# Default target
#
all: init build_libraries build_modules build_fds

#
# Initialization target: print build information and create necessary directories
#
init:
\t-@echo Building ... $(PLATFORM_NAME)-$(PLATFORM_VERSION) [${build_architecture_list}]
\t${create_directory_command} $(FV_DIR) > NUL 2>&1
\t${BEGIN}${create_directory_command} $(BUILD_DIR)${separator}${architecture} > NUL 2>&1
\t${END}
\t${BEGIN}${create_directory_command} $(BUILD_DIR)${separator}${directory_to_be_created} > NUL 2>&1
\t${END}
#
# library build target
#
libraries: init build_libraries

#
# module build target
#
modules: init build_libraries build_modules

#
# Flash Device Image Target
#
fds: init build_libraries build_modules build_fds

#
# Build all libraries:
#
build_libraries:
\t${BEGIN}cd $(WORKSPACE)${separator}${library_build_directory}
\t$(MAKE) $(MAKE_FLAGS) lbuild
\t${END}cd $(BUILD_DIR)

#
# Build all modules:
#
build_modules:
\t${BEGIN}cd $(WORKSPACE)${separator}${module_build_directory}
\t$(MAKE) $(MAKE_FLAGS) pbuild
\t${END}cd $(BUILD_DIR)

#
# Build Flash Device Image
#
build_fds:
\t-@echo Generating flash image, if any ...
${BEGIN}\tGenFds -f ${fdf_file} -o $(BUILD_DIR) -p ${active_platform}${END}

#
# Clean intermediate files
#
clean:
\t${BEGIN}cd $(WORKSPACE)${separator}${library_build_directory}
\t$(MAKE) $(MAKE_FLAGS) clean
\t${END}${BEGIN}cd $(WORKSPACE)${separator}${module_build_directory}
\t$(MAKE) $(MAKE_FLAGS) clean
\t${END}cd $(BUILD_DIR)

#
# Clean all generated files except to makefile
#
cleanall:
\t${BEGIN}cd $(WORKSPACE)${separator}${library_build_directory}
\t$(MAKE) $(MAKE_FLAGS) cleanall
\t${END}${BEGIN}cd $(WORKSPACE)${separator}${module_build_directory}
\t$(MAKE) $(MAKE_FLAGS) cleanall
\t${END}cd $(BUILD_DIR)

#
# Clean all library files
#
cleanlib:
\t${BEGIN}cd $(WORKSPACE)${separator}${library_build_directory}
\t$(MAKE) $(MAKE_FLAGS) cleanlib
\t${END}cd $(BUILD_DIR)

'''

class Makefile(object):
    def __init__(self, info, opt):
        if isinstance(info, ModuleBuildInfo):
            self.ModuleInfo = info
            self.PlatformInfo = info.PlatformInfo
            self.PackageInfo = info.PackageInfo
            self.ModuleBuild = True
            
            self.BuildType = "mbuild"
            if self.ModuleInfo.IsLibrary:
                self.BuildType = "lbuild"
                
            self.BuildFileList = []
            self.ObjectFileList = []
            self.ObjectBuildTargetList = []

            self.FileDependency = []
            self.LibraryBuildCommandList = []
            self.LibraryFileList = []
            self.LibraryMakefileList = []
            self.LibraryBuildDirectoryList = []

        elif type(info) == type({}):    # and isinstance(info, PlatformBuildInfo):
            self.PlatformInfo = info
            self.ModuleBuild = False
            self.ModuleBuildCommandList = []
            self.ModuleMakefileList = []
            self.ModuleBuildDirectoryList = self.GetModuleBuildDirectoryList()
            self.LibraryBuildDirectoryList = self.GetLibraryBuildDirectoryList()
        else:
            raise Exception("Non-buildable item!")

        self.Opt = opt
        self.BuildWithPch = opt["ENABLE_PCH"]
        self.BuildWithLocalLib = opt["ENABLE_LOCAL_LIB"]
        self.IntermediateDirectoryList = []

    def PrepareDirectory(self):
        if self.ModuleBuild:
            CreateDirectory(path.join(self.ModuleInfo.WorkspaceDir, self.PlatformInfo.BuildDir))
            CreateDirectory(path.join(self.ModuleInfo.WorkspaceDir, self.ModuleInfo.BuildDir))
            CreateDirectory(path.join(self.ModuleInfo.WorkspaceDir, self.ModuleInfo.DebugDir))

    def Generate(self, file=None, makeType=gMakeType):
        if self.ModuleBuild:
            return self.GenerateModuleMakefile(file, makeType)
        else:
            return self.GeneratePlatformMakefile(file, makeType)
    
    def GeneratePlatformMakefile(self, file=None, makeType=gMakeType):
        separator = gDirectorySeparator[makeType]

        activePlatform = self.PlatformInfo.values()[0].Platform
        platformInfo = self.PlatformInfo.values()[0]
        
        outputDir = platformInfo.OutputDir
        if os.path.isabs(outputDir):
            self.PlatformBuildDirectory = outputDir
        else:
            self.PlatformBuildDirectory = "$(WORKSPACE)" + separator + outputDir

        makefileName = gMakefileName[makeType]
        makefileTemplateDict = {
            "makefile_header"           : MakefileHeader % makefileName,
            "platform_name"             : platformInfo.Name,
            "platform_guid"             : platformInfo.Guid,
            "platform_version"          : platformInfo.Version,
            "platform_relative_directory": platformInfo.SourceDir,
            "platform_output_directory" : platformInfo.OutputDir,
            "platform_build_directory"  : self.PlatformBuildDirectory,

            "toolchain_tag"             : platformInfo.ToolChain,
            "build_target"              : platformInfo.BuildTarget,
            "build_architecture_list"   : " ".join(self.PlatformInfo.keys()),
            "architecture"              : self.PlatformInfo.keys(),
            "separator"                 : separator,
            "create_directory_command"  : "-@mkdir",
            "directory_to_be_created"   : self.IntermediateDirectoryList,
            "library_build_directory"   : self.LibraryBuildDirectoryList,
            "module_build_directory"    : self.ModuleBuildDirectoryList,
            "fdf_file"                  : platformInfo.FdfFileList,
            "active_platform"           : activePlatform.DescFilePath
        }

        self.PrepareDirectory()

        autoGenMakefile = AutoGenString()
        autoGenMakefile.Append(gPlatformMakefileTemplate, makefileTemplateDict)
        #print autoGenMakefile.String

        filePath = ""
        if file == None:
            filePath = path.join(platformInfo.WorkspaceDir, platformInfo.MakefileDir, makefileName)
        else:
            filePath = file

        self.SaveFile(filePath, str(autoGenMakefile))
        return filePath

    def GenerateModuleMakefile(self, file=None, makeType=gMakeType):
        if makeType in self.ModuleInfo.CustomMakefile and self.ModuleInfo.CustomMakefile[makeType] != "":
            return self.GenerateCustomBuildMakefile(file, makeType)

        separator = gDirectorySeparator[makeType]

        if os.path.isabs(self.PlatformInfo.OutputDir):
            self.PlatformBuildDirectory = self.PlatformInfo.OutputDir
        else:
            self.PlatformBuildDirectory = "$(WORKSPACE)" + separator + self.PlatformInfo.OutputDir

        self.ProcessSourceFileList(makeType)
        self.ProcessDependentLibrary(makeType)

        entryPoint = "_ModuleEntryPoint"
        if self.ModuleInfo.Arch == "EBC":
            entryPoint = "EfiStart"

        makefileName = gMakefileName[makeType]
        makefileTemplateDict = {
            "makefile_header"           : MakefileHeader % makefileName,
            "platform_name"             : self.PlatformInfo.Name,
            "platform_guid"             : self.PlatformInfo.Guid,
            "platform_version"          : self.PlatformInfo.Version,
            "platform_relative_directory": self.PlatformInfo.SourceDir,
            "platform_output_directory" : self.PlatformInfo.OutputDir,

            "package_name"              : self.PackageInfo.Name,
            "package_guid"              : self.PackageInfo.Guid,
            "package_version"           : self.PackageInfo.Version,
            "package_relative_directory": self.PackageInfo.SourceDir,

            "module_name"               : self.ModuleInfo.Name,
            "module_guid"               : self.ModuleInfo.Guid,
            "module_version"            : self.ModuleInfo.Version,
            "module_type"               : self.ModuleInfo.ModuleType,
            "module_file_base_name"     : self.ModuleInfo.FileBase,
            "module_relative_directory" : self.ModuleInfo.SourceDir,

            "architecture"              : self.ModuleInfo.Arch,
            "toolchain_tag"             : self.ModuleInfo.ToolChain,
            "build_target"              : self.ModuleInfo.BuildTarget,

            "platform_build_directory"  : self.PlatformBuildDirectory,

            "separator"                 : separator,
            "default_tool_flags"        : self.PlatformInfo.DefaultToolOption.values(),
            "platform_tool_flags"       : self.PlatformInfo.BuildOption.values(),
            "module_tool_flags"         : self.ModuleInfo.BuildOption.values(),

            "tool_code"                 : self.PlatformInfo.ToolPath.keys(),
            "tool_path"                 : self.PlatformInfo.ToolPath.values(),

            "module_entry_point"        : entryPoint,
            "source_file"               : self.BuildFileList,
            #"auto_generated_file"       : self.AutoGenBuildFileList,
            "include_path_prefix"       : "-I",
            "include_path"              : self.ModuleInfo.IncludePathList,
            "object_file"               : self.ObjectFileList,
            "library_file"              : self.LibraryFileList,
            "common_dependency_file"    : self.CommonFileDependency,
            "create_directory_command"  : "-@mkdir",
            "directory_to_be_created"   : self.IntermediateDirectoryList,
            "dependent_library_build_directory" : self.LibraryBuildDirectoryList,
            #"dependent_library_makefile"        : [path.join(bdir, makefileName) for bdir in self.LibraryBuildDirectoryList],
            "object_build_target"               : self.ObjectBuildTargetList,
            "build_type"                        : self.BuildType,
        }
        
        self.PrepareDirectory()
        
        autoGenMakefile = AutoGenString()
        autoGenMakefile.Append(gModuleMakefileTemplate, makefileTemplateDict)
        #print autoGenMakefile.String
        
        filePath = ""
        if file == None:
            filePath = path.join(self.ModuleInfo.WorkspaceDir, self.ModuleInfo.MakefileDir, makefileName)
        else:
            filePath = file

        self.SaveFile(filePath, str(autoGenMakefile))
        return filePath

    def GenerateCustomBuildMakefile(self, file=None, makeType=gMakeType):
        separator = gDirectorySeparator[makeType]

        if os.path.isabs(self.PlatformInfo.OutputDir):
            self.PlatformBuildDirectory = self.PlatformInfo.OutputDir
        else:
            self.PlatformBuildDirectory = "$(WORKSPACE)" + separator + self.PlatformInfo.OutputDir

        customMakefile = open(os.path.join(self.ModuleInfo.WorkspaceDir, self .ModuleInfo.CustomMakefile[makeType]), 'r').read()
        
        makefileName = gMakefileName[makeType]
        makefileTemplateDict = {
            "makefile_header"           : MakefileHeader % makefileName,
            "platform_name"             : self.PlatformInfo.Name,
            "platform_guid"             : self.PlatformInfo.Guid,
            "platform_version"          : self.PlatformInfo.Version,
            "platform_relative_directory": self.PlatformInfo.SourceDir,
            "platform_output_directory" : self.PlatformInfo.OutputDir,

            "package_name"              : self.PackageInfo.Name,
            "package_guid"              : self.PackageInfo.Guid,
            "package_version"           : self.PackageInfo.Version,
            "package_relative_directory": self.PackageInfo.SourceDir,

            "module_name"               : self.ModuleInfo.Name,
            "module_guid"               : self.ModuleInfo.Guid,
            "module_version"            : self.ModuleInfo.Version,
            "module_type"               : self.ModuleInfo.ModuleType,
            "module_file_base_name"     : self.ModuleInfo.FileBase,
            "module_relative_directory" : self.ModuleInfo.SourceDir,

            "architecture"              : self.ModuleInfo.Arch,
            "toolchain_tag"             : self.ModuleInfo.ToolChain,
            "build_target"              : self.ModuleInfo.BuildTarget,

            "platform_build_directory"  : self.PlatformBuildDirectory,

            "separator"                 : separator,
            "default_tool_flags"        : self.PlatformInfo.DefaultToolOption.values(),
            "platform_tool_flags"       : self.PlatformInfo.BuildOption.values(),
            "module_tool_flags"         : self.ModuleInfo.BuildOption.values(),

            "tool_code"                 : self.PlatformInfo.ToolPath.keys(),
            "tool_path"                 : self.PlatformInfo.ToolPath.values(),

            "create_directory_command"  : "-@mkdir",
            "directory_to_be_created"   : self.IntermediateDirectoryList,
            "dependent_library_build_directory" : self.LibraryBuildDirectoryList,
            "custom_makefile_content"   : customMakefile
        }

        self.PrepareDirectory()

        autoGenMakefile = AutoGenString()
        autoGenMakefile.Append(gCustomMakefileTemplate, makefileTemplateDict)
        #print autoGenMakefile.String

        filePath = ""
        if file == None:
            filePath = path.join(self.ModuleInfo.WorkspaceDir, self.ModuleInfo.MakefileDir, makefileName)
        else:
            filePath = file

        self.SaveFile(filePath, str(autoGenMakefile))
        return filePath

    def SaveFile(self, file, content):
        # print "######",file,"######"
        f = None
        if os.path.exists(file):
            f = open(file, 'r')
            if content == f.read():
                f.close()
                return
            f.close()
        f = open(file, "w")
        f.write(content)
        f.close()

    def ProcessSourceFileList(self, makeType=gMakeType):
        rule = self.PlatformInfo.BuildRule
        separator = gDirectorySeparator[makeType]

        self.BuildFileList = []
        self.ObjectFileList = []
        self.ObjectBuildTargetList = []
        self.AutoGenBuildFileList = []
        self.IntermediateDirectoryList = []

        fileBuildTemplatetList = []
        forceIncludedFile = []

        for f in self.ModuleInfo.AutoGenFileList:
            fpath = path.join(self.ModuleInfo.DebugDir, f)
            fdir = path.dirname(f)
            if fdir == "":
                fdir = "."
            fname = path.basename(f)
            fbase, fext = path.splitext(fname)

            ftype = rule.FileTypeMapping[fext]
            if ftype == "C-Header":
                forceIncludedFile.append(fpath)
            if ftype not in rule.Makefile[makeType]:
                continue

            #ftype = "AutoGen-Code"
            #self.AutoGenBuildFileList.append(f)
            self.BuildFileList.append(fpath)
            self.ObjectFileList.append(fdir + separator + fbase + ".obj")

            fileBuildTemplatetList.append({
                                   "string" : rule.Makefile[makeType][ftype],
                                   "ftype"  : ftype,
                                   "fpath"  : fpath,
                                   "fdir"   : fdir,
                                   "fname"  : fname,
                                   "fbase"  : fbase,
                                   "fext"   : fext,
                                   "fdep"   : "",
                                   "sep"    : separator,
                                   })
##            autoGen = AutoGenString()
##            autoGen.Append(rule.Makefile[makeType][ftype],
##                           {"fdir":".", "fbase":base, "fext":ext, "fname":name, "sep":os.path.sep,
##                            "fdep":self.GetDependencyList(os.path.join(self.ModuleInfo.DebugDir, f), self.ModuleInfo.IncludePathList)})
##            self.ObjectBuildTargetList.append(autoGen.String)

        fileList = self.ModuleInfo.SourceFileList
        for f in fileList:
            fpath = os.path.join(self.ModuleInfo.SourceDir, f)
            fname = path.basename(f)
            fbase, fext = path.splitext(fname)
            fdir = path.dirname(f)
            
            if fdir == "":
                fdir = "."
            elif fdir not in self.IntermediateDirectoryList:
                self.IntermediateDirectoryList.append(fdir)
                
            if fbase.endswith("Gcc"):
                continue
            
            ftype = rule.FileTypeMapping[fext]
            if ftype not in rule.Makefile[makeType]:
                continue

            self.BuildFileList.append(fpath)
            self.ObjectFileList.append(fdir + separator + fbase + ".obj")
            
            fileBuildTemplatetList.append({
                                   "string" : rule.Makefile[makeType][ftype],
                                   "ftype"  : ftype,
                                   "fpath"  : fpath,
                                   "fdir"   : fdir,
                                   "fname"  : fname,
                                   "fbase"  : fbase,
                                   "fext"   : fext,
                                   "fdep"   : "",
                                   "sep"    : separator,
                                   })
##            autoGen = AutoGenString()
##            autoGen.Append(rule.Makefile[makeType][ftype],
##                           {"fdir":basedir, "fbase":base, "fext":ext, "fname":name, "sep":gDirectorySeparator[makeType],
##                           "dep":self.GetDependencyList(os.path.join(self.ModuleInfo.SourceDir, f), self.ModuleInfo.IncludePathList)
##                           })
##            self.ObjectBuildTargetList.append(autoGen.String)

        #
        # Search dependency file list for each source file
        #
        self.FileDependency = self.GetFileDependency(forceIncludedFile)
        depSet = set(self.FileDependency.values()[0])
        for dep in self.FileDependency.values():
            depSet &= set(dep)
        #
        # Extract comman files list in the dependency files
        #
        self.CommonFileDependency = forceIncludedFile + list(depSet)
        for f in self.FileDependency:
            newDepSet = set(self.FileDependency[f])
            newDepSet -= depSet
            self.FileDependency[f] = list(newDepSet)

        for template in fileBuildTemplatetList:
            makefileString = AutoGenString()
            template["fdep"] = self.FileDependency[template["fpath"]]
            makefileString.Append(template["string"], template)
            self.ObjectBuildTargetList.append(makefileString)

    def ProcessDependentLibrary(self, makeType=gMakeType):
        for libm in self.ModuleInfo.DependentLibraryList:
            libf = str(libm)
            libp = path.dirname(libf)
            base = path.basename(libf).split(".")[0]
            self.LibraryBuildDirectoryList.append(libp + gDirectorySeparator[makeType] + base)
            self.LibraryFileList.append(libm.BaseName + ".lib")

    def GetPlatformBuildDirectory(self):
        if os.path.isabs(self.PlatformInfo.OutputDir):
            return self.PlatformInfo.OutputDir
        else:
            return os.path.join("$(WORKSPACE)", self.PlatformInfo.OutputDir)

    def GetAutoGeneratedFileList(self):
        if self.ModuleInfo.IsLibrary:
            return ""
        else:
            return "AutoGen.c"

    def GetFileDependency(self, forceList):
        cwd = os.getcwd()
        os.chdir(self.ModuleInfo.WorkspaceDir)
        dependency = {}
        for f in self.BuildFileList:
            #f = os.path.join(self.ModuleInfo.SourceDir, f)
            dependency[f] = self.GetDependencyList(f, forceList, self.ModuleInfo.IncludePathList)
##        for f in  self.AutoGenBuildFileList:
##            f = os.path.join(self.ModuleInfo.DebugDir, f)
##            dependency[f] = self.GetDependencyList(f, self.ModuleInfo.IncludePathList)
        os.chdir(cwd)
        return dependency

    def GetDependencyList(self, file, forceList, searchPathList):
        cwd = os.getcwd()
        os.chdir(self.ModuleInfo.WorkspaceDir)

        fileStack = [file] + forceList
        dependencyList = []
        while len(fileStack) > 0:
            f = fileStack.pop()

            currentFileDependencyList = []
            if f in gDependencyDatabase:
                currentFileDependencyList = gDependencyDatabase[f]
                for dep in currentFileDependencyList:
                    if dep not in fileStack and dep not in dependencyList:
                        fileStack.append(dep)
            else:
                fd = open(f, 'r')
                fileContent = fd.read()
                fd.close()
                if fileContent[0] == 0xff or fileContent[0] == 0xfe:
                    fileContent = unicode(fileContent, "utf-16")
                includedFileList = gIncludePattern.findall(fileContent)

                currentFilePath = os.path.dirname(f)
                for inc in includedFileList:
                    inc = os.path.normpath(inc)
                    for searchPath in [currentFilePath] + searchPathList:
                        filePath = os.path.join(searchPath, inc)
                        if not os.path.exists(filePath) or filePath in currentFileDependencyList:
                            continue
                        currentFileDependencyList.append(filePath)
                        if filePath not in fileStack and filePath not in dependencyList:
                            fileStack.append(filePath)
                        break
                    #else:
                    #    print "###", inc, "was not found in any given path:",f,"\n   ", "\n    ".join(searchPathList)
                gDependencyDatabase[f] = currentFileDependencyList
            dependencyList.extend(currentFileDependencyList)
        dependencyList = list(set(dependencyList))  # remove duplicate ones

        os.chdir(cwd)
        dependencyList.append(file)
        return dependencyList

    def GetModuleBuildDirectoryList(self):
        dirList = []
        for arch in self.PlatformInfo:
            for ma in self.PlatformInfo[arch].ModuleAutoGenList:
                dirList.append(ma.BuildInfo.BuildDir)
        return dirList

    def GetLibraryBuildDirectoryList(self):
        dirList = []
        for arch in self.PlatformInfo:
            for la in self.PlatformInfo[arch].LibraryAutoGenList:
                dirList.append(la.BuildInfo.BuildDir)
        return dirList

# This acts like the main() function for the script, unless it is 'import'ed into another
# script.
if __name__ == '__main__':
    print "Running Operating System =", sys.platform
    ewb = WorkspaceBuild()
    #print ewb.Build.keys()
    
    myArch = ewb.Build["IA32"].Arch
    #print myArch

    myBuild = ewb.Build["IA32"]
    
    myWorkspace = ewb
    apf = ewb.TargetTxt.TargetTxtDictionary["ACTIVE_PLATFORM"][0]
    myPlatform = myBuild.PlatformDatabase[os.path.normpath(apf)]

    for mf in myBuild.ModuleDatabase:
        #mf = "MdePkg\\Library\\BaseLib\\BaseLib.inf"
        #if mf in myPlatform.Modules and mf in myBuild.ModuleDatabase:
        #print mf

        myModule = myBuild.ModuleDatabase[mf]

        myPackage = FindModuleOwner(myModule.DescFilePath, myBuild.PackageDatabase)

        myToolchain = ewb.TargetTxt.TargetTxtDictionary["TOOL_CHAIN_TAG"][0]
        #print myToolchain

        myBuildTarget = ewb.TargetTxt.TargetTxtDictionary["TARGET"][0]
        #print myBuildTarget

        myBuildOption = {
            "ENABLE_PCH"        :   False,
            "ENABLE_LOCAL_LIB"  :   True,
        }

        myMakefile = Makefile(myModule, myPackage, myPlatform, myWorkspace, myToolchain, myBuildTarget,
                              myArch, myBuildOption, "nmake")

        myMakefile.NewGenerate()
