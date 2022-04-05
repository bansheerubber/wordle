import sys

wordle = [word.strip() for word in open("wordle-truth.txt").readlines()]

index = int(sys.argv[1])
word = wordle[index]
guesses = sys.argv[2:]
last_guess = guesses[-1]

result = ""
correct = 0
for i in range(0, 5):
	if word[i] == last_guess[i]:
		result += last_guess[i].upper()
		correct += 1
	elif last_guess[i] in word:
		result += last_guess[i]
	else:
		result += "-" + last_guess[i]

if correct != 5:
	print(result)
else:
	print("correct")