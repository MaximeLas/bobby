#!/bin/bash
#
# Demo script for Bobby Orchestrator
#
# This simulates a meeting transcript and shows how the orchestrator responds.
#
# Usage: ./tests/demo_orchestrator.sh
#        (run from the project root)

TRANSCRIPT_FILE="sandbox/meeting_transcript.txt"
PROGRESS_FILE="sandbox/agent_progress.txt"

echo "========================================================"
echo "Bobby Orchestrator - Demo"
echo "========================================================"
echo ""
echo "This demo will:"
echo "1. Create a mock meeting transcript"
echo "2. Show you how to run the orchestrator"
echo "3. Simulate triggers"
echo ""
echo "Press ENTER to continue..."
read

# Ensure sandbox directory exists
mkdir -p sandbox

# Clean up old files
echo "Cleaning up old files..."
rm -f "$TRANSCRIPT_FILE" "$PROGRESS_FILE"
echo ""

# Create initial transcript
echo "Creating mock meeting transcript..."
cat > "$TRANSCRIPT_FILE" <<EOF
[14:23:15] Speaker A: So we need a pricing page for the website
[14:23:22] Speaker B: Yeah, three tiers would be good
[14:23:35] Speaker A: Make sure it matches our existing design system
[14:23:42] Speaker B: Should have monthly and annual options
EOF

echo "Created $TRANSCRIPT_FILE with initial discussion"
echo ""
echo "Content:"
cat "$TRANSCRIPT_FILE"
echo ""
echo "========================================================"
echo ""

echo "Now you need to start the orchestrator in another terminal:"
echo ""
echo "  uv run python3 -m bobby.orchestrator"
echo ""
echo "Once the orchestrator is running, press ENTER to add the trigger..."
read

# Add trigger
echo ""
echo "Adding trigger: 'Hey Bobby, please build this'"
echo "[14:23:55] Speaker A: Hey Bobby, please build this" >> "$TRANSCRIPT_FILE"
echo ""
echo "Check the orchestrator terminal. You should see:"
echo "  - Trigger detected"
echo "  - Bobby would say: 'Sure, working on it now'"
echo "  - Agent launch attempt"
echo ""
echo "========================================================"
echo ""

echo "NOTES:"
echo ""
echo "1. If Claude Code CLI is installed, it will actually launch"
echo "   the agent with the meeting context as a prompt."
echo ""
echo "2. The agent would then write to $PROGRESS_FILE as it works."
echo ""
echo "3. If the agent asks a question (writes 'QUESTION:'), you can"
echo "   test the resume flow by adding an answer and 'Thank you, Bobby'"
echo ""
echo "Example to test resume:"
echo "  echo '[14:26:00] Speaker A: Use blue for the primary button' >> $TRANSCRIPT_FILE"
echo "  echo '[14:26:05] Speaker A: Thank you, Bobby' >> $TRANSCRIPT_FILE"
echo ""
echo "========================================================"
echo ""
echo "Demo complete!"
echo ""

# Cleanup prompt
echo "Clean up test files? (y/n)"
read -r cleanup
if [ "$cleanup" = "y" ]; then
    rm -f "$TRANSCRIPT_FILE" "$PROGRESS_FILE"
    echo "Cleaned up."
fi
