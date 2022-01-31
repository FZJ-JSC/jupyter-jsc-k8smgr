#!/bin/bash
echo "Hello World from my Script"

if [[ <hook_load_project_specific_kernel> -eq 1 ]]; then
    echo "Use project kernel"
fi

if [[ <hook_multiple_keys> -eq 1 ]]; then
    echo "Use multiple_keys hook"
fi
