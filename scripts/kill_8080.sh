#!/bin/bash
echo "Killing process on port 8080..."
fuser -k 8080/tcp
echo "Done."
