import sys

SH = 0; RE = 1; RA = 2; LA = 3;

labels = ["nsubj", "csubj", "nsubjpass", "csubjpass", "dobj", "iobj", "ccomp", "xcomp", "nmod", "advcl", "advmod", "neg", "aux", "auxpass", "cop", "mark", "discourse", "vocative", "expl", "nummod", "acl", "amod", "appos", "det", "case", "compound", "mwe", "goeswith", "name", "foreign", "conj", "cc", "punct", "list", "parataxis", "remnant", "dislocated", "reparandum", "root", "dep", "nmod:npmod", "nmod:tmod", "nmod:poss", "acl:relcl", "cc:preconj", "compound:prt"]

def read_sentences():
    sentences = []
    sentence = []
    for line in sys.stdin:
        line = line.strip()
        
        # 1. Handle empty lines (sentence boundaries)
        if not line:
            if len(sentence) > 0:
                sentences.append(sentence)
                sentence = []
            continue
            
        token = line.split("\t")
        
        # 2. ROBUST FILTERING: 
        # Skip lines that are too short (metadata) OR don't start with a number
        # This removes lines like "<Sentence id='1'>", "))", etc.
        if len(token) < 10 or not token[0].isdigit():
            continue

        sentence.append(token)
        
    if len(sentence) > 0:
        sentences.append(sentence)
    return sentences

def attach_orphans(arcs, n):
    attached = []
    for (h, d, l) in arcs:
        attached.append(d)
    for i in range(1, n):
        if not i in attached:
            arcs.append((0, i, "root"))

def print_tab(arcs, words, tags):
    hs = {}
    ls = {}
    for (h, d, l) in arcs:
        hs[d] = h
        ls[d] = l
    for i in range(1, len(words)):
        print("\t".join([words[i], tags[i], str(hs[i]), ls[i]]))
    print()
        
def print_tree(root, arcs, words, indent):
    if root == 0:
        print(" ".join(words[1:]))
    children = [(root, i, l) for i in range(len(words)) for l in labels if (root, i, l) in arcs]
    for (h, d, l) in sorted(children):
        print(indent + l + "(" + words[h] + "_" + str(h) + ", " + words[d] + "_" + str(d) + ")")
        print_tree(d, arcs, words, indent + "  ")

def transition(trans, stack, buffer, arcs):
    if trans[0] == SH:
        if buffer:
            stack.insert(0, buffer.pop(0))
    if trans[0] == RE:
        # pop the item from the stack if the stack is not empty and the top of the stack is not the root
        if stack and stack[0] != 0:
            stack.pop(0)
    if trans[0] == RA:
        # add an arc from the top of the stack to the first item in the buffer with the label specified in the transition, and pop the item from the stack
        if stack and buffer:
            arcs.append((stack[0], buffer[0], trans[1]))
            stack.insert(0, buffer.pop(0))
    if trans[0] == LA:
        # add an arc from the first item in the buffer to the top of the stack with the label specified in the transition, and pop the item from the stack
        if stack and buffer and stack[0] != 0:
            arcs.append((buffer[0], stack[0], trans[1]))
            stack.pop(0)
    return stack, buffer, arcs

def oracle(stack, buffer, heads, labels):
    # add code for missing transitions: (RE, "_"), (RA, label), (LA, label)
    if not stack or not buffer:
        return (SH, "_")
    
    s = stack[0]
    b = buffer[0]

    # Left Arc condition
    if heads[s] == b:
        return (LA, labels[s])
    
    # Right Arc condition
    elif heads[b] == s:
        return (RA, labels[b])
    
    # Reduce condition
    else:
        # s have any children in buffer?
        has_child_in_buffer = any(heads[i] == s for i in buffer)

        # has s fouyd its head?
        s_has_head = heads[s] not in buffer

        if s_has_head and not has_child_in_buffer:
            return (RE, "_")
    
    # default
    return (SH, "_")

def print_conll(sentence, arcs):
    """
    Prints the parse result in CoNLL format (Tab-separated).
    """
    # Create a map: dependent_index -> (head_index, label)
    # Note: arcs use 1-based indexing for words, 0 for ROOT
    dep_map = {}
    for head, dep, label in arcs:
        dep_map[dep] = (head, label)
        
    # Iterate through the original sentence tokens
    # sentence list is 0-indexed, corresponding to words 1..n
    for i, token in enumerate(sentence):
        word_idx = i + 1
        
        # Get head and label from the parse result
        # If a word is not in arcs (shouldn't happen with attach_orphans), default to 0
        head, label = dep_map.get(word_idx, (0, "root"))
        
        # Update the token's Head (col 6) and Label (col 7)
        # We ensure we preserve the original columns
        token[6] = str(head)
        token[7] = label
        
        print("\t".join(token))
    
    print("") # Blank line between sentences

def parse(sentence):
    # 1. Skip empty sentences
    if not sentence:
        return

    # 2. EXTRACT AND PAD DATA
    # We add dummy elements at index 0 so that words[1] is the first word, 
    # matching the parser's 1-based indexing.
    try:
        # Standard CoNLL indices: 1=Word, 6=Head, 7=Label
        words = ["ROOT"] + [sentence[i][1] for i in range(len(sentence))]
        heads = [-1] + [int(sentence[i][6]) for i in range(len(sentence))]
        labels = ["_"] + [sentence[i][7] for i in range(len(sentence))]
    except (ValueError, IndexError):
        # Skip sentences with non-integer heads or missing columns [cite: 103]
        return

    # 3. INITIALIZE PARSER STATE
    stack = [0]  # Stack starts with ROOT
    buffer = [x for x in range(1, len(words))] # Buffer starts at first word
    arcs = []
    
    # 4. PARSING LOOP WITH INFINITE LOOP PROTECTION
    # Max iterations safety: prevents the while loop from running forever [cite: 89]
    max_iterations = len(words) * 4 
    iterations = 0

    while (buffer or len(stack) > 1) and iterations < max_iterations:
        iterations += 1
        
        # Get the move from the oracle [cite: 62]
        trans = oracle(stack, buffer, heads, labels)
        
        # --- SAFETY OVERRIDES ---
        # If the oracle suggests an impossible move based on the current state,
        # we force a move to ensure the parser continues[cite: 67].
        
        # Cannot Shift or Right-Arc if buffer is empty
        if not buffer and trans[0] in [SH, RA]:
            if len(stack) > 1:
                trans = (RE, "_")
            else:
                break
                
        # Cannot Reduce or Left-Arc if stack is just ROOT
        if len(stack) <= 1 and trans[0] in [RE, LA]:
            if buffer:
                trans = (SH, "_")
            else:
                break

        # Record state to check for zero progress
        pre_buffer_len = len(buffer)
        pre_stack_len = len(stack)
        
        # Perform the move
        stack, buffer, arcs = transition(trans, stack, buffer, arcs)
        
        # If the transition logic failed to change the state, force progress
        if len(buffer) == pre_buffer_len and len(stack) == pre_stack_len:
            if buffer:
                stack.insert(0, buffer.pop(0))
            else:
                break

    # 5. POST-PROCESSING AND OUTPUT
    # Attach any words that missed a head to ROOT [cite: 85]
    attach_orphans(arcs, len(words))
    
    # Print the resulting tree in the requested format [cite: 86]
    # print_tree(0, arcs, words, "")

    # Print the resulting tree in CoNLL format for the pipeline
    print_conll(sentence, arcs)
    
if __name__ == "__main__":
    tab_format = False
    if len(sys.argv) == 2 and sys.argv[1] == "tab":
        tab_format = True
    for sentence in read_sentences():
        parse(sentence)
