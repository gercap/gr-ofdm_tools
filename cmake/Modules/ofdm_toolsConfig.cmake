INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_OFDM_TOOLS ofdm_tools)

FIND_PATH(
    OFDM_TOOLS_INCLUDE_DIRS
    NAMES ofdm_tools/api.h
    HINTS $ENV{OFDM_TOOLS_DIR}/include
        ${PC_OFDM_TOOLS_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    OFDM_TOOLS_LIBRARIES
    NAMES gnuradio-ofdm_tools
    HINTS $ENV{OFDM_TOOLS_DIR}/lib
        ${PC_OFDM_TOOLS_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(OFDM_TOOLS DEFAULT_MSG OFDM_TOOLS_LIBRARIES OFDM_TOOLS_INCLUDE_DIRS)
MARK_AS_ADVANCED(OFDM_TOOLS_LIBRARIES OFDM_TOOLS_INCLUDE_DIRS)

