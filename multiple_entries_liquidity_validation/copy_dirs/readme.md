My suggestion for the next 14 days:
Day 1-2: Build a basic version that just copies files one-way from source to replica. No logging, no hashing, no loops. Just get the copy working.
Day 3-4: Add the deletion logic (remove files in replica that don't exist in source).
Day 5-6: Add MD5 hashing to detect changed files.
Day 7-8: Add the periodic loop (N iterations with sleep interval).
Day 9-10: Add proper logging to both file and console.
Day 11-12: Add command line argument parsing.
Day 13: Test everything with edge cases — empty folders, nested folders, big files.
Day 14: Clean up, review, submit.
