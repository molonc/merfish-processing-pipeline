#!/bin/bash
if (( $# != 1 )); then
    echo 'Usage: export_atlas XP_YAML'
    exit 1
fi


merfish-pipe run $1 --stage index
merfish-pipe run $1 --stage atlas_export