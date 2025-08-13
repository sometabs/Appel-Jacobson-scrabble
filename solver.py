from letter_tree import basic_english
from board import sample_board
import points as sp


class SolveState:
    def __init__(self, dictionary, board, rack):
        self.dictionary = dictionary
        self.board = board
        self.rack = rack
        self.cross_check_results = None
        self.direction = None
        self.best_move_info = [None, 0, None, (-1,-1), None] # [word, score, direction, starting_position, board]

    def before(self, pos):
        row, col = pos
        if self.direction == 'across':
            return row, col - 1
        else:
            return row - 1, col

    def after(self, pos):
        row, col = pos
        if self.direction == 'across':
            return row, col + 1
        else:
            return row + 1, col

    def before_cross(self, pos):
        row, col = pos
        if self.direction == 'across':
            return row - 1, col
        else:
            return row, col - 1

    def after_cross(self, pos):
        row, col = pos
        if self.direction == 'across':
            return row + 1, col
        else:
            return row, col + 1

    def legal_move(self, word, last_pos):
        board_if_we_played_that = self.board.copy()
        play_pos = last_pos
        word_idx = len(word) - 1
        while word_idx >= 0:
            board_if_we_played_that.set_tile(play_pos, word[word_idx])
            word_idx -= 1
            play_pos = self.before(play_pos)

        # Calculate the score for the played word and update the best move 
        score = 0
        if( len(word) == 1 ): # Special case for single letter words ('a', 'i')
            score = self.calculate_score([[[word, play_pos]]])
        else:
            score = self.calculate_score(self.detect_all_board_words(board_if_we_played_that))
        print(f"Word: {word}, Score: {score}, "
                  f"Direction: {self.direction}, Starting position: {self.before(play_pos)}")
        
        if score > self.best_move_info[1]:
            self.best_move_info[0] = word
            self.best_move_info[1] = score
            self.best_move_info[2] = self.direction
            self.best_move_info[3] = self.after(play_pos)
            self.best_move_info[4] = board_if_we_played_that


    def cross_check(self):
        result = dict()
        for pos in self.board.all_positions():
            if self.board.is_filled(pos):
                continue
            letters_before = ""
            scan_pos = pos
            while self.board.is_filled(self.before_cross(scan_pos)):
                scan_pos = self.before_cross(scan_pos)
                letters_before = self.board.get_tile(scan_pos) + letters_before
            letters_after = ""
            scan_pos = pos
            while self.board.is_filled(self.after_cross(scan_pos)):
                scan_pos = self.after_cross(scan_pos)
                letters_after = letters_after + self.board.get_tile(scan_pos)
            if len(letters_before) == 0 and len(letters_after) == 0:
                legal_here = list('abcdefghijklmnopqrstuvwxyz')
            else:
                legal_here = []
                for letter in 'abcdefghijklmnopqrstuvwxyz':
                    word_formed = letters_before + letter + letters_after
                    if self.dictionary.is_word(word_formed):
                        legal_here.append(letter)
            result[pos] = legal_here
        return result

    def find_anchors(self):
        anchors = []
        for pos in self.board.all_positions():
            empty = self.board.is_empty(pos)
            neighbor_filled = self.board.is_filled(self.before(pos)) or \
                              self.board.is_filled(self.after(pos)) or \
                              self.board.is_filled(self.before_cross(pos)) or \
                              self.board.is_filled(self.after_cross(pos))
            if empty and neighbor_filled:
                anchors.append(pos)
        return anchors

    def before_part(self, partial_word, current_node, anchor_pos, limit):
        self.extend_after(partial_word, current_node, anchor_pos, False)
        if limit > 0:
            for next_letter in current_node.children.keys():
                if next_letter in self.rack:
                    self.rack.remove(next_letter)
                    self.before_part(
                        partial_word + next_letter,
                        current_node.children[next_letter],
                        anchor_pos,
                        limit - 1
                    )
                    self.rack.append(next_letter)

    def extend_after(self, partial_word, current_node, next_pos, anchor_filled):
        if not self.board.is_filled(next_pos) and current_node.is_word and anchor_filled:
            self.legal_move(partial_word, self.before(next_pos))
        if self.board.in_bounds(next_pos):
            if self.board.is_empty(next_pos):
                for next_letter in current_node.children.keys():
                    if next_letter in self.rack and next_letter in self.cross_check_results[next_pos]:
                        self.rack.remove(next_letter)
                        self.extend_after(
                            partial_word + next_letter,
                            current_node.children[next_letter],
                            self.after(next_pos),
                            True
                        )
                        self.rack.append(next_letter)
            else:
                existing_letter = self.board.get_tile(next_pos)
                if existing_letter in current_node.children.keys():
                    self.extend_after(
                        partial_word + existing_letter,
                        current_node.children[existing_letter],
                        self.after(next_pos),
                        True
                    )

    def find_all_options(self):
        for direction in ['across', 'down']:
            self.direction = direction
            anchors = self.find_anchors()
            self.cross_check_results = self.cross_check()
            for anchor_pos in anchors:
                if self.board.is_filled(self.before(anchor_pos)):
                    scan_pos = self.before(anchor_pos)
                    partial_word = self.board.get_tile(scan_pos)
                    while self.board.is_filled(self.before(scan_pos)):
                        scan_pos = self.before(scan_pos)
                        partial_word = self.board.get_tile(scan_pos) + partial_word
                    pw_node = self.dictionary.lookup(partial_word)
                    if pw_node is not None:
                        self.extend_after(
                            partial_word,
                            pw_node,
                            anchor_pos,
                            False
                        )
                else:
                    limit = 0
                    scan_pos = anchor_pos
                    while self.board.is_empty(self.before(scan_pos)) and self.before(scan_pos) not in anchors:
                        limit = limit + 1
                        scan_pos = self.before(scan_pos)
                    self.before_part("", self.dictionary.root, anchor_pos, limit)

    # Detect all words formed on the board after playing a word
    # Returns a list containing lists of tokenized words which contain lists of each letter and their positions
    # For example, if the board has the letters 'train' horizontally and 'hi' vertically, the return result will be:
    # [ [['t', (7, 7)], ['r', (7, 8)], ['a', (7, 9)], ['i', (7, 10)], ['n', (7, 11)]], [['h',(6,10)], ['i', (7, 10)]] ]
    def detect_all_board_words(self, board_if_we_played_that):

        curr_board = self.board
        letters_and_positions = []

        # Horizontal words
        for row in range(self.board.size):
            curr_letter_and_position = []
            is_new_word = False
            for col in range(self.board.size):
                if board_if_we_played_that.get_tile((row,col)) != None:
                    curr_letter_and_position.append([board_if_we_played_that.get_tile((row,col)), (row, col)])
                    # Check if the word is new or already exists on the current board (self.board)
                    # The word is considered new if a new letter is detected
                    if board_if_we_played_that.get_tile((row,col)) != curr_board.get_tile((row,col)):
                        is_new_word = True
                else :
                    if is_new_word and len(curr_letter_and_position)>1: # If the word is new and has more than one letter
                        letters_and_positions.append(curr_letter_and_position)
                    curr_letter_and_position= []
                    is_new_word = False
            if is_new_word and len(curr_letter_and_position)>1 :
                letters_and_positions.append(curr_letter_and_position)

        
        # Vertical words
        for col in range(self.board.size):
            curr_letter_and_position = []
            is_new_word = False
            for row in range(self.board.size):
                if board_if_we_played_that.get_tile((row,col)) != None:
                    curr_letter_and_position.append([board_if_we_played_that.get_tile((row,col)), (row, col)])
                    if board_if_we_played_that.get_tile((row,col)) != curr_board.get_tile((row,col)):
                        is_new_word = True
                else :
                    if is_new_word and len(curr_letter_and_position)>1:
                        letters_and_positions.append(curr_letter_and_position)
                    curr_letter_and_position = []
                    is_new_word = False
            if is_new_word and len(curr_letter_and_position)>1:
                letters_and_positions.append(curr_letter_and_position)

        return letters_and_positions
    
    # Calculate the score of the current board setup after playing the word
    # It takes into account the letter scores, bonus tiles, and the possibility of using all letters in the rack
    # Returns the total score of the current board setup
    def calculate_score(self, letters_and_positions):

        total_score = 0
        
        for word in letters_and_positions:
            word_score = 0
            word_bonuses = []
            for lp in word :
                letter = lp[0]
                letter_position = lp[1]
                has_bonus = False
                for tile in sp.bonus_tiles:
                    bonus_positions = sp.bonus_tiles[tile]
                    if letter_position in bonus_positions:
                        if tile == "DL":
                            word_score += (sp.letter_scores[letter]*2)
                            has_bonus = True
                        elif tile == "TL":
                            word_score+= (sp.letter_scores[letter]*3)
                            has_bonus = True
                        else :
                            word_bonuses.append(tile)
                
                # If the letter does not have a bonus, add its normal score
                if not has_bonus:
                    word_score += sp.letter_scores[letter]
        
            # Add word bonuses 
            for bonus in word_bonuses:
                if bonus == "TW":
                    word_score*=3
                else :
                    word_score*=2
            #print("Word: ",word, "Score: ", word_score)
            total_score += word_score
            
            # If the AI can place all the 7 letters in the rack, add 50 points
            if len(self.rack) == 0:
                total_score+=50
                
        return total_score
    
    def print_best_move(self):
        if self.best_move_info[0] is not None:
            print(f"Best move: {self.best_move_info[0]}, Score: {self.best_move_info[1]}, "
                  f"Direction: {self.best_move_info[2]}, Starting position: {self.best_move_info[3]}")
            print("Board after the best move:")
            print(self.best_move_info[4])
        else:
            print("No valid moves found.")

        

solver = SolveState(basic_english(), sample_board(), ['e', 'a', 'f', 'b', 'i', 't','s'])#['a', 'r', 'i', 'e', 'b', 'i','w']
print("Initial Board:")
print(solver.board)
print("\n\n\n\nAll options:")
solver.find_all_options()
print("\n\n\n\n")
solver.print_best_move()