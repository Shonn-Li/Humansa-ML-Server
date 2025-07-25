#!/bin/bash
# Check ML server status and ports

echo "==================================="
echo "ML Server Status Check"
echo "==================================="
echo ""

# Check port 6001
echo "📍 Port 6001 Status:"
if lsof -i:6001 > /dev/null 2>&1; then
    echo "   ⚠️  Port 6001 is IN USE"
    lsof -i:6001
else
    echo "   ✅ Port 6001 is FREE"
fi
echo ""

# Check port 5001
echo "📍 Port 5001 Status:"
if lsof -i:5001 > /dev/null 2>&1; then
    echo "   ⚠️  Port 5001 is IN USE"
    lsof -i:5001
else
    echo "   ✅ Port 5001 is FREE"
fi
echo ""

# Check Python ML server processes
echo "🐍 Python ML Server Processes:"
PROCS=$(ps aux | grep -E "python.*main\.py" | grep -v grep)
if [ ! -z "$PROCS" ]; then
    echo "$PROCS" | while read line; do
        echo "   $line" | awk '{print "PID: " $2 " | " $11 " " $12 " " $13}'
    done
else
    echo "   ✅ No ML server processes running"
fi
echo ""

# Check if server is responding
echo "🌐 Server Health Check:"
for port in 5001 6001; do
    echo -n "   Port $port: "
    if curl -s http://localhost:$port/api/debug/health > /dev/null 2>&1; then
        echo "✅ Server responding"
    else
        echo "❌ Not responding"
    fi
done
echo ""