cmake_minimum_required(VERSION 3.14)
project(sports_analyzer_ai LANGUAGES CXX)

set(BINARY_NAME "sports_analyzer_ai")

cmake_policy(SET CMP0063 NEW)

set(CMAKE_INSTALL_PREFIX "${CMAKE_BINARY_DIR}/install")
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

if(DEFINED ENV{ENABLE_DART_PROFILING})
  add_compile_definitions(ENABLE_DART_PROFILING)
endif()

add_subdirectory("flutter")
add_subdirectory("runner")

install(TARGETS ${BINARY_NAME} RUNTIME DESTINATION "${CMAKE_INSTALL_PREFIX}")

install(FILES "${FLUTTER_LIBRARY}" DESTINATION "${CMAKE_INSTALL_PREFIX}")
install(FILES "${FLUTTER_ICU_DATA_FILE}" DESTINATION "${CMAKE_INSTALL_PREFIX}")
install(FILES "${CPP_FLUTTER_PLUGINS_LIB}" DESTINATION "${CMAKE_INSTALL_PREFIX}")
install(CODE "set(x64_redist_dir \"${MSVC_REDIST_DIRECTORY}\")")
install(CODE [[include(InstallRequiredSystemLibraries)]])
install(CODE [[cmake_install(DIRECTORY "${x64_redist_dir}/" DESTINATION "${CMAKE_INSTALL_PREFIX}" FILES_MATCHING PATTERN "*.dll")]])
