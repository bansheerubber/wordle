file = open("frequency.txt")
other_file = open("new_frequency", "w")
for line in file:
	line = line.strip()
	word = line.split(" ")[0].lower()
	if len(word) == 5:
		write = True
		for letter in word:
			if ord(letter) < 97 or ord(letter) > 122:
				write = False
		
		if write:
			other_file.write(line + "\n")

file.close()
other_file.close()