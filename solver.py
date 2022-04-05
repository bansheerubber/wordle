from enum import Enum
import sys
from subprocess import Popen, PIPE
import copy
import math
import os
from scipy import stats
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import pickle

file = open("wordle-truth.txt")
wordle = [word.strip() for word in file.readlines()]
file.close()
class Player:
	def __init__(self, word):
		self.word = word

	def guess(self, guess):
		result = ""
		correct = 0
		for i in range(0, 5):
			if self.word[i] == guess[i]:
				result += guess[i].upper()
				correct += 1
			elif guess[i] in self.word:
				result += guess[i]
			else:
				result += "-" + guess[i]
		
		if correct != 5:
			return result
		else:
			return "correct"

words = open("list.txt").readlines()
words = list(set([word.strip() for word in words] + wordle))
words_length = len(words)
# print(words_length)

word_frequency_file = open("five-letter-frequency.txt")
word_frequency_total = 0
for line in word_frequency_file:
	_, frequency = line.strip().split(" ")
	word_frequency_total += int(frequency)
word_frequency_file.close()

word_frequency_file = open("five-letter-frequency.txt")
word_frequency = {}
word_frequency_sigmoid_total = 0
for line in word_frequency_file:
	word, frequency = line.strip().split(" ")
	word_frequency[word] = int(frequency)
	word_frequency[word] = 1 / (1 + math.e ** (-0.004 * (-len(word_frequency) + 1000)))
	word_frequency_sigmoid_total += word_frequency[word]
word_frequency_file.close()

def get_word_frequency(word):
	if word not in word_frequency:
		return 0
	return word_frequency[word]
	# return 1

cached_keys = {}

def compute_key(guess, word, cached=False):
	if cached:
		return cached_keys[guess][word]
	
	letter_counts = {}
	for letter in word:
		if letter not in letter_counts:
			letter_counts[letter] = 1
		else:
			letter_counts[letter] += 1

	# key = ""
	key = 0
	for i in range(0, 5):
		if guess[i] == word[i]:
			# key += "G"
			key = key | (3 << (i * 2))
			letter_counts[guess[i]] -= 1
		elif guess[i] in word and letter_counts[guess[i]] > 0:
			# key += "Y"
			key = key | (2 << (i * 2))
			letter_counts[guess[i]] -= 1
		else:
			# key += "R"
			key = key | (1 << (i * 2))
	return key

if not os.path.exists("word-key-cache"):
	for word1 in words:
		cached_keys[word1] = {}
		print(word1)
		for word2 in words:
			cached_keys[word1][word2] = int(compute_key(word1, word2))
	file = open("word-key-cache", "wb")
	pickle.dump(cached_keys, file, protocol=pickle.HIGHEST_PROTOCOL)
	file.close()
else:
	file = open("word-key-cache", "rb")
	cached_keys = pickle.load(file)
	file.close()

word_sets = {}

# gneerate lists that we can index
for word in words:
	for i in range(0, 5):
		letter = word[i]
		if letter not in word_sets:
			word_sets[letter] = {}
		
		if i not in word_sets[letter]:
			word_sets[letter][i] = set()

		word_sets[letter][i].add(word)

class CommandType(Enum):
	LETTER_AT_POSITION = 0
	LETTER_IN_WORD = 1
	EXCLUDE_LETTER = 2

class Command:
	def __init__(self, type, parameters):
		self.type = type
		self.parameters = parameters
	
	def __str__(self):
		if self.type == CommandType.LETTER_AT_POSITION:
			return f"LETTER_AT_POSITION: {self.parameters}"
		elif self.type == CommandType.LETTER_IN_WORD:
			return f"LETTER_IN_WORD: {self.parameters}"
		elif self.type == CommandType.EXCLUDE_LETTER:
			return f"EXCLUDE_LETTER: {self.parameters}"
	
	def __repr__(self):
		return self.__str__()


total = 0
for word in words:
	total += get_word_frequency(word)

starting_entropy = 0
for word in words:
	probability = get_word_frequency(word) / total
	if probability != 0:
		starting_entropy += probability * math.log2(1 / probability)

class Knowledgebase:
	def __init__(self):
		self.excluded_letters = set()
		self.letters_at_position = set()
		self.letters_in_word = {}
		self.entropy = 0
		self.guess_count = 1

		self.uncertainties = []

		self.last_entropy = starting_entropy

	# update the knowledgebase
	def add_knowledge(self, letter_list, knowledge=None):
		if knowledge == None:
			knowledge = (self.excluded_letters, self.letters_at_position, self.letters_in_word)
		
		for position in range(0, 5):
			letter, letter_type = letter_list[position]
			if letter_type == CommandType.LETTER_AT_POSITION:
				knowledge[1].add((letter, position))
			elif letter_type == CommandType.LETTER_IN_WORD:
				if letter not in knowledge[2]:
					knowledge[2][letter] = set()
				knowledge[2][letter].add(position)
			elif letter_type == CommandType.EXCLUDE_LETTER:
				knowledge[0].add(letter)
	
	def simulate_add_knowledge(self, guess, truth):
		player = Player(truth)
		result = player.guess(guess)

		self.simulated_excluded_letters = self.excluded_letters.copy()
		self.simulated_letters_at_position = self.letters_at_position.copy()
		self.simulated_letters_in_word = copy.deepcopy(self.letters_in_word)

		self.add_knowledge(decode_input(result), (self.simulated_excluded_letters, self.simulated_letters_at_position, self.simulated_letters_in_word))
	
	def generate_command_list(self, knowledge=None):
		if knowledge == None:
			knowledge = (self.excluded_letters, self.letters_at_position, self.letters_in_word)
		
		command_list = []
		for letter, position in knowledge[1]:
			command_list.append(Command(CommandType.LETTER_AT_POSITION, (letter, position)))
		
		for letter, positions in knowledge[2].items():
			command_list.append(Command(CommandType.LETTER_IN_WORD, (letter, list(positions))))
		
		for letter in knowledge[0]:
			command_list.append(Command(CommandType.EXCLUDE_LETTER, (letter)))

		return command_list

	def get_list(self, knowledge=None):
		result_set = set()

		command_list = self.generate_command_list(knowledge)

		# generate initial set
		command = command_list[0]
		if command.type == CommandType.LETTER_AT_POSITION:
			result_set = set(word_sets[command.parameters[0]][command.parameters[1]])
		elif command.type == CommandType.LETTER_IN_WORD:
			for i in range(0, 5):
				if i not in command.parameters[1]:
					if len(result_set) == 0:
						result_set = set(word_sets[command.parameters[0]][i])
					elif i in word_sets[command.parameters[0]]:
						result_set = result_set.union(word_sets[command.parameters[0]][i])
			for i in range(0, 5): # above set is overly inclusive, reduce it down a little
					if i in command.parameters[1]:
						result_set = result_set.difference(word_sets[command.parameters[0]][i])
		elif command.type == CommandType.EXCLUDE_LETTER:
			for word in words:
				if command.parameters[0] not in word:
					result_set.add(word)

		# reduce set down
		for i in range(1, len(command_list)):
			command = command_list[i]
			if command.type == CommandType.LETTER_AT_POSITION:
				result_set = result_set.intersection(word_sets[command.parameters[0]][command.parameters[1]])
			elif command.type == CommandType.LETTER_IN_WORD:
				for i in range(0, 5):
					if i in command.parameters[1]:
						result_set = result_set.difference(word_sets[command.parameters[0]][i])
				temp_set = set(result_set)
				for word in result_set:
					if command.parameters[0] not in word:
						temp_set.remove(word)
				result_set = temp_set
			elif command.type == CommandType.EXCLUDE_LETTER:
				temp_set = set()
				for word in result_set:
					if command.parameters[0] not in word:
						temp_set.add(word)
				result_set = temp_set

		def heuristic(word):
			entropy, frequency = self.compute_expected_entropy(word, result_set)

			def entropy_to_rounds_left(value):
				# return 1.2 * ((value + 0.3) ** 0.4)
				return 1 + 0.33928799 * value
			
			# print(word, self.last_entropy, entropy, entropy_to_rounds_left(self.last_entropy - entropy))

			# print(frequency, frequency * self.guess_count, (1 - frequency) * (self.guess_count + entropy_to_rounds_left(self.last_entropy - entropy)))

			return frequency * self.guess_count + (1 - frequency) * (self.guess_count + entropy_to_rounds_left(self.last_entropy - entropy) - 0.95)
		
		self.last_entropy = 0
		total = 0
		for word in result_set:
			total += get_word_frequency(word)
		
		for word in result_set:
			probability = get_word_frequency(word) / total
			if probability != 0:
				self.last_entropy += probability * math.log2(1 / probability)
		self.uncertainties.append(self.last_entropy)
		
		# sort by heuristic
		return sorted(words, key=heuristic)
	
	def compute_expected_entropy(self, guess, word_list):
		distribution = {}
		unique = 0
		total_word_frequency = 0
		for word in word_list:
			key = compute_key(guess, word, True)
			
			if key not in distribution:
				distribution[key] = 0

			distribution[key] += get_word_frequency(word)
			unique += get_word_frequency(word)
		
		entropy = 0
		for value in distribution.values():
			if unique != 0:
				probability = value / unique
				if probability != 0:
					entropy += probability * math.log2(1 / probability)
	
		return (entropy, get_word_frequency(guess) / unique if guess in word_list else 0)

	def guess(self):
		guesses = self.get_list()
		guess = guesses[0]
		self.guess_count += 1
		return guess

def decode_input(value):
	result = []
	last_letter = None
	for letter in value:
		if letter != "-" and last_letter != "-":
			if ord(letter) < 97:
				result.append((letter.lower(), CommandType.LETTER_AT_POSITION))
			else:
				result.append((letter.lower(), CommandType.LETTER_IN_WORD))
		elif last_letter == "-":
			result.append((letter.lower(), CommandType.EXCLUDE_LETTER))
		last_letter = letter
	return result

if len(sys.argv) < 2:
	solver = Knowledgebase()
	while True:
		value = input("Guess result: ")
		if value == "won":
			print("Congrats on your hard work")
			exit(0)

		solver.add_knowledge(decode_input(value))
		guess = solver.guess()
		print("Best guess: " + guess)
else:
	aggregate = 0
	average_entropy = 0
	total = 0

	histogram = {
		1: 0,
		2: 0,
		3: 0,
		4: 0,
		5: 0,
		6: 0,
	}

	uncertainties_list = []

	start = 0
	end = len(wordle)
	peek = False
	if len(sys.argv) == 3:
		start = int(sys.argv[2])
		end = start + 1
		peek = True
	elif len(sys.argv) == 4:
		start = int(sys.argv[2])
		end = int(sys.argv[3])

	for index in range(start, end):
		solver = Knowledgebase()
		player = Player(wordle[index])
		guesses = ["arose"]

		print(wordle[index])

		score = -1
		for i in range(0, 6):
			result = player.guess(guesses[-1])
			if peek == True:
				print("Guessing: " + guesses[-1])
				print(result)

			if result != "correct":
				solver.add_knowledge(decode_input(result))
				guesses.append(solver.guess())
			else:
				score = i + 1
				for j in range(0, len(solver.uncertainties)):
					uncertainty = solver.uncertainties[j]
					uncertainties_list.append((uncertainty, score - j - 1))
				break
		
		if score < 0:
			print("dnf on " + wordle[index] + " " + str(index))
		else:
			aggregate += score
			histogram[score] += 1
			total += 1
	
	# means, x_axis, _ = stats.binned_statistic([i[0] for i in uncertainties_list], [i[1] for i in uncertainties_list], bins=20)
	# data = []
	# for i in range(0, len(means)):
	# 	data.append(((x_axis[i] + x_axis[i + 1]) / 2, means[i]))
	# model = LinearRegression().fit([[i[0]] for i in data], [[i[1]] for i in data])
	# print(f"{model.intercept_} {model.coef_}")

	# plt.bar(x_axis[:-1], means, width=0.1)
	# plt.show()

	if peek == False:
		print(f"average first entropy: {average_entropy}")
		print(f"average: {aggregate / total}")
		print(histogram)
