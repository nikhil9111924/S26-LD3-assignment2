import sys

# --- HELPER FUNCTIONS ---

def is_projective(heads):
    """
    Checks if a dependency tree is projective.
    Arc (i, j) is non-projective if it crosses arc (k, l).
    """
    n = len(heads)
    # heads has a dummy at index 0, so valid indices are 1..n-1
    # We iterate through all pairs of arcs
    for i in range(1, n):
        if heads[i] == -1: continue # Root or skip
        
        # Arc 1: (parent_i -> i)
        min_i, max_i = sorted((heads[i], i))
        
        for j in range(i + 1, n):
            if heads[j] == -1: continue
            
            # Arc 2: (parent_j -> j)
            min_j, max_j = sorted((heads[j], j))
            
            # Check for crossing:
            # One endpoint of Arc 2 is strictly inside Arc 1, 
            # and the other is strictly outside.
            if (min_i < min_j < max_i < max_j) or \
               (min_j < min_i < max_j < max_i):
                return False
    return True

def get_parents(heads):
    """Returns a list where list[i] is the parent of word i."""
    return heads

def get_children(heads):
    """Returns a dictionary mapping parents to list of children."""
    children = {}
    for i in range(len(heads)):
        h = heads[i]
        if h not in children: children[h] = []
        children[h].append(i)
    return children

# --- ENCODING (Non-Projective -> Pseudo-Projective) ---

def lift_arcs(words, heads, labels):
    """
    Iteratively lifts non-projective arcs to their grandparent 
    until the tree is projective.
    Encodes the move in the label: 'LABEL^HEAD_LABEL'
    """
    # Max iterations to prevent infinite loops in bad trees
    for _ in range(len(words)): 
        if is_projective(heads):
            break
            
        # Find the first non-projective arc
        # (Simplified: in a full system we'd find the smallest non-proj arc)
        for i in range(1, len(heads)):
            if heads[i] == -1: continue # Skip ROOT
            
            # Check if this specific arc (heads[i] -> i) crosses any other
            is_crossing = False
            min_i, max_i = sorted((heads[i], i))
            
            for j in range(1, len(heads)):
                if i == j or heads[j] == -1: continue
                min_j, max_j = sorted((heads[j], j))
                
                if (min_i < min_j < max_i < max_j) or \
                   (min_j < min_i < max_j < max_i):
                    is_crossing = True
                    break
            
            if is_crossing:
                # LIFT OPERATION
                current_head = heads[i]
                grandparent = heads[current_head]
                
                # If current head is ROOT (0), we can't lift further.
                if current_head == 0:
                    continue
                    
                # Lift to grandparent
                heads[i] = grandparent
                
                # Encode path in label: "MyLabel^IntermediateHeadLabel"
                # We append the label of the arc we just jumped over
                intermediate_label = labels[current_head]
                labels[i] = f"{labels[i]}^{intermediate_label}"
                
                # Break to re-evaluate projectivity from scratch
                break
                
    return heads, labels

# --- DECODING (Pseudo-Projective -> Non-Projective) ---

def sink_arcs(words, heads, labels):
    """
    Decodes the labels to move arcs back down to their true parents.
    Looks for labels with '^'.
    """
    # We repeat until no changes are made (handling multi-level lifts)
    changed = True
    while changed:
        changed = False
        children = get_children(heads)
        
        for i in range(1, len(heads)):
            if '^' in labels[i]:
                # Decode the label: "RealLabel^SearchTarget"
                parts = labels[i].rsplit('^', 1)
                base_label = parts[0]
                target_head_label = parts[1]
                
                current_head = heads[i]
                
                # Search children of current_head for the "intermediate" node
                # The intermediate node should have the label 'target_head_label'
                found_new_head = -1
                
                if current_head in children:
                    for sibling in children[current_head]:
                        if sibling == i: continue # Skip self
                        if labels[sibling] == target_head_label:
                            found_new_head = sibling
                            break
                            
                # If we found the intermediate node, move the arc down!
                if found_new_head != -1:
                    heads[i] = found_new_head
                    labels[i] = base_label # Remove the ^Tag
                    changed = True
                    
    return heads, labels

# --- MAIN IO ---

def process_conll(mode):
    sentence_buffer = []
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            if sentence_buffer:
                process_sentence(sentence_buffer, mode)
                sentence_buffer = []
                print("") # Print blank line between sentences
            continue
            
        token = line.split("\t")
        # Validate CoNLL line
        if len(token) >= 10 and token[0].isdigit():
            sentence_buffer.append(token)
            
    if sentence_buffer:
        process_sentence(sentence_buffer, mode)

def process_sentence(sentence, mode):
    # Extract columns (1-based index simulation)
    # ids = [int(tok[0]) for tok in sentence] # Not strictly needed if sequential
    words = ["ROOT"] + [tok[1] for tok in sentence]
    heads = [-1] + [int(tok[6]) for tok in sentence]
    labels = ["_"] + [tok[7] for tok in sentence]
    
    if mode == 'encode':
        heads, labels = lift_arcs(words, heads, labels)
    elif mode == 'decode':
        heads, labels = sink_arcs(words, heads, labels)
        
    # Print back in CoNLL format
    for i, tok in enumerate(sentence):
        # Update HEAD (col 6) and LABEL (col 7)
        tok[6] = str(heads[i+1])
        tok[7] = labels[i+1]
        print("\t".join(tok))

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ['encode', 'decode']:
        sys.stderr.write("Usage: python3 projectivize.py [encode|decode] < input.conll > output.conll\n")
        sys.exit(1)
        
    process_conll(sys.argv[1])