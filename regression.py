import subprocess
import re

ranges = [(0, 577), (577, 1154), (1154, 1731), (1731, 2309)]

matcher = re.compile("average: (.+?\n)")

processes = []
for start, end in ranges:
	process = subprocess.Popen(["python", "solver.py", "test", str(start), str(end)], stdout=subprocess.PIPE, cwd="/home/me/Projects/wordle")
	processes.append(process)

averages = 0
count = 0
for process in processes:
	stdout, _ = process.communicate()

	if match := matcher.search(stdout.decode("ascii")):
		averages += float(match.group(1).strip())
		count += 1

if count != 0:
	value = averages / count
	print(value)
else:
	print("fail")