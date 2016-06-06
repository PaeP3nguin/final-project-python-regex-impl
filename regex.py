#!python2

import re
import sys

class State(object):
    """Base representation of a state in a NFA"""

    # Class variable used to assign IDs to classes
    id_count = 1

    def __init__(self, state_id=None):
        self.next_states = []
        if state_id != None:
            self.state_id = state_id
        else:
            self.state_id = State.id_count
            State.id_count += 1

    def match(self, char):
        """Attempt to match a character

        Returns:
            If the match succeeded, a list of states to consider next.
            Otherwise, returns an empty list.
        """
        raise NotImplementedError

    def add_next_state(self, next_state):
        """Connect this state to another one"""
        self.next_states.append(next_state)

    def get_id(self):
        """Returns the unique ID for this state"""
        return self.state_id


class Char(State):
    """A state that matches a character"""

    def __init__(self, char):
        super(Char, self).__init__()
        if char == '.':
            self.match_any = True
        else:
            self.match_char = char
            self.match_any = False

    def __repr__(self):
        return "Char{id: %d, char: %s, next_states: %d}" % (self.state_id, self.match_char, len(self.next_states))

    def match(self, char):
        if self.match_any or self.match_char == char:
            return self.next_states
        else:
            return []


class Split(State):
    """An empty state with some number of possible next states"""

    def match(self, char):
        matches = []
        for state in self.next_states:
            if type(state) is End:
                matches.append(state)
            else:
                matches.extend(state.match(char))
        return matches

    def __repr__(self):
        return "Split{id: %d, next_states: %d}" % (self.state_id, len(self.next_states))


class Start(Split):
    """The start state"""

    def __init__(self):
        super(Start, self).__init__(0)

    def __repr__(self):
        return "Start{id: %d, next_states: %d}" % (self.state_id, len(self.next_states))


class End(State):
    """The end state"""

    def __init__(self):
        super(End, self).__init__(-1)

    def match(self, char):
        # Always return empty list
        return []

    def __repr__(self):
        return "End{id: %d, next_states: %d}" % (self.state_id, len(self.next_states))


class NFA():
    """Represents an NFA with a start and end state and any number of states in between

    The end state must be reachable from the start state.
    The start and end states might be the same (in the case of a character).
    """

    def __init__(self, start=None, end=None, other_nfa=None):
        self.start_state = start
        self.end_state = end

        if other_nfa:
            if not start:
                self.start_state = Split()
            if not end:
                self.end_state = Split()
            for nfa in other_nfa:
                self.wrap(nfa)

    def connect(self, next_nfa):
        """Connect the end of this NFA to the start of another NFA"""
        self.end_state.add_next_state(next_nfa.start_state)
        self.end_state = next_nfa.end_state

    def loop(self):
        """Connect the end of this NFA to its own start"""
        self.end_state.add_next_state(self.start_state)

    def bypass(self):
        """Connect the start of this NFA to its own end"""
        self.start_state.add_next_state(self.end_state)

    def wrap(self, other_nfa):
        """Wrap another NFA between the start and end states of this NFA"""
        self.start_state.add_next_state(other_nfa.start_state)
        other_nfa.end_state.add_next_state(self.end_state)


def build_nfa(pattern):
    """Builds a NFA from a regex pattern"""
    State.id_count = 1
    # start = Start()
    # curr_nfa = [NFA(start, start)]
    curr_nfa = [None]
    nfa_stack = [[]]
    for i, char in enumerate(pattern):
        if char in ('?', '*', '+'):
            # Unary operators
            if len(nfa_stack) == 0:
                raise SyntaxError("Invalid syntax near char " + str(i))

            wrap = None
            # wrap = NFA(other_nfa=[nfa_stack[-1].pop()])

            if char == "?":
                # Zero or one
                wrap = NFA(other_nfa=[nfa_stack[-1].pop()])
                wrap.bypass()
            elif char == "*":
                # Zero or more
                wrap = NFA(other_nfa=[nfa_stack[-1].pop()])
                wrap.bypass()
                wrap.loop()
            elif char == "+":
                # One or more
                wrap = nfa_stack[-1].pop()
                wrap.loop()

            nfa_stack[-1].append(wrap)
        elif char == "|":
            # OR operator
            if len(nfa_stack[-1]) == 1:
                finalize_nfa_stack(nfa_stack, curr_nfa)
                nfa_stack[-1].append(curr_nfa[-1])
                curr_nfa[-1] = None
        elif char == "(":
            # start group
            curr_nfa.append(None)
            nfa_stack.append([])
        elif char == ")":
            # end group
            finalize_nfa_stack(nfa_stack, curr_nfa)
            nfa_stack.pop()
            nfa_stack[-1].append(curr_nfa.pop())
        else:
            # Character literal
            char_state = Char(char)
            char_nfa = NFA(char_state, char_state)

            if pattern[i-1] == "|":
                nfa_stack[-1].append(char_nfa)
            elif nfa_stack[-1]:
                nfa_stack[-1][-1].connect(char_nfa)
            else:
                nfa_stack[-1].append(char_nfa)
            # if pattern[i-1] == "|":
            #     nfa_stack[-1].append(char_nfa)
            # else:
            #     finalize_nfa_stack(nfa_stack, curr_nfa)
            #     nfa_stack[-1] = [char_nfa]

    # assert len(curr_nfa) == 1

    finalize_nfa_stack(nfa_stack, curr_nfa)

    end = End()
    curr_nfa[0].connect(NFA(end, end))
    return curr_nfa[0]

def finalize_nfa_stack(nfa_stack, curr_nfa):
    """Helper function to connect the NFAs on the stack with the current NFA"""
    if len(nfa_stack[-1]) > 1:
        wrap = NFA(other_nfa=nfa_stack[-1])
        if curr_nfa[-1]:
            curr_nfa[-1].connect(wrap)
        else:
            curr_nfa[-1] = wrap
    elif len(nfa_stack[-1]) == 1:
        if curr_nfa[-1]:
            curr_nfa[-1].connect(nfa_stack[-1].pop())
        else:
            curr_nfa[-1] = nfa_stack[-1].pop()

def match_pattern(pattern, string):
    nfa = build_nfa(pattern)
    start = nfa.start_state
    states = set()
    states.add(start)
    for char in string:
        if len(states) == 0:
            return False
        next_states = []
        for s in states:
            next_states.extend(s.match(char))
        states = set(next_states)
    return nfa.end_state in states

def main():
    regex = ""

    try:
        re.compile(regex)
        test = build_nfa("a")
        test = build_nfa("ab")
        test = build_nfa("a|b")
        test = build_nfa("a|(bc)")
        test = build_nfa("(a)")
        test = build_nfa("(a|b)")
        test = build_nfa("(a|b)|(ab)")
        test = build_nfa("(a|b)|(ab)|c")
        test = build_nfa("(a|b)+|(ab)|c")
        test = build_nfa("(a|b)+?|(ab)|c")
        test = build_nfa("(a|b)*|(ab)|c")
        test = build_nfa("(a|b)?|(ab)|c")
        test = build_nfa("(ca*t|lion)+.*(dog)?")
        print test
        print match_pattern("a", "a")
        print match_pattern("a", "ab")
        print match_pattern("ab", "ab")
        print match_pattern("a+", "ab")
        print match_pattern("a+", "aa")
        print match_pattern("a+", "aaa")
        print match_pattern("a+a+", "aaa")
        print match_pattern("a*a+", "aaa")
        print match_pattern("(ca*t|lion)+.*(dog)?", "catsdog")
    except re.error:
        print("Invalid regex!")

if __name__ == '__main__':
    sys.exit(int(main() or 0))
