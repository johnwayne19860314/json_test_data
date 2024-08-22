#!/bin/bash

# Define the source branch
# source_branch="feature-branch"

# Define the target folder
target_folder="src/"

# # Checkout the target branch (the one you want to merge changes into)
# git checkout main

# # Merge the source branch into the current branch, without committing
# git merge --no-commit --no-ff $source_branch

# List all files in the target directory and resolve conflicts using --ours strategy
for file in $(git ls-files $target_folder); do
    if git ls-files --unmerged | grep -q "$file"; then
        # Resolve conflicts in favor of our changes
        git checkout --ours $file
        git add $file
    fi
done

# Commit the merge with a message
git commit -m "Merged changes from "

#git commit -m "Merged changes from $source_branch into $(git branch --show-current) using --ours strategy"
