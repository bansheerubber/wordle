file = open("wordle-truth.txt")
letter_frequency = {}
total = 0
words = []
for line in file:
	word = line.strip()
	found = set()
	for letter in word:
		if letter not in letter_frequency:
			letter_frequency[letter] = 0
		
		if letter not in found:
			letter_frequency[letter] += 1
			found.add(letter)
		total += 1
	words.append(word)

letter_frequency = {k: v / total for k, v in sorted(letter_frequency.items(), key=lambda item: item[1], reverse=True)}

candidates = []
most_popular_letters = list(letter_frequency.keys())[:6]
for word in words:
	count = 0
	found = set()
	for letter in most_popular_letters:
		if letter in word and letter not in found:
			count += 1
			found.add(letter)
	
	if count == 5:
		candidates.append(word)

print(candidates)

file.close()
