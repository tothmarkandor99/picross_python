#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "picross::stdutils" for configuration "Release"
set_property(TARGET picross::stdutils APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(picross::stdutils PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/stdutils.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS picross::stdutils )
list(APPEND _IMPORT_CHECK_FILES_FOR_picross::stdutils "${_IMPORT_PREFIX}/lib/stdutils.lib" )

# Import target "picross::picross" for configuration "Release"
set_property(TARGET picross::picross APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(picross::picross PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/picross.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS picross::picross )
list(APPEND _IMPORT_CHECK_FILES_FOR_picross::picross "${_IMPORT_PREFIX}/lib/picross.lib" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
