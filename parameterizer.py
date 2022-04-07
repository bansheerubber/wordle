import subprocess
import re

centers = [2500, 3000, 3500, 4000, 4500]
slopes = [0.0001, 0.001, 0.002]

ranges = [(0, 577), (577, 1154), (1154, 1731), (1731, 2309)]

matcher = re.compile("average: (.+?\n)")

file = open("sigmoid-results", "w")
for center in centers:
	for slope in slopes:
		print(f"testing center {center} slope {slope}")
		
		processes = []
		for start, end in ranges:
			process = subprocess.Popen(["python", "solver.py", "test", str(start), str(end), "--sigmoid-center", f"{center}", "--sigmoid-slope", f"{slope}"], stdout=subprocess.PIPE, cwd="/home/me/Projects/wordle")
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
			file.write(f"{center} {slope} {value}\n")
		else:
			file.write(f"{center} {slope} fail\n")
file.close()
