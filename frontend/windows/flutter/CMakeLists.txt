cmake_minimum_required(VERSION 3.14)
project(flutter)

set(EPHEMERAL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/ephemeral")

include(${EPHEMERAL_DIR}/generated_config.cmake OPTIONAL RESULT_VARIABLE HAS_BACKEND)
if(NOT HAS_BACKEND)
  message(FATAL_ERROR "Flutter backend not available. Run flutter pub get first.")
endif()

set(FLUTTER_LIBRARY "${EPHEMERAL_DIR}/flutter_windows.dll")

add_library(flutter INTERFACE)
target_include_directories(flutter INTERFACE
  "${EPHEMERAL_DIR}"
)
target_link_libraries(flutter INTERFACE "${FLUTTER_LIBRARY}.lib")

add_custom_target(flutter_assemble VERBATIM
  COMMAND ${CMAKE_COMMAND} -E env
    "FLUTTER_ROOT=${FLUTTER_ROOT}"
    ${FLUTTER_TOOL_ENVIRONMENT}
    "${FLUTTER_ROOT}/bin/flutter.bat"
      assemble
      --output=.\\flutter_build
      ${FLUTTER_BUILD_ARGS}
  COMMENT "Assembling Flutter resources..."
)
