SH = 0; RE = 1; RA = 2; LA = 3;
labels = ["det", "nsubj", "case", "nmod", "root"]

def attach_orphans(arcs, n):
    attached = []
    for (h, d, l) in arcs:
        attached.append(d)
    for i in range(1, n):
        if not i in attached:
            arcs.append((0, i, "root"))

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

def parse():
    words = "root the cat is on the mat today".split()
    stack = [0]
    buffer = [x for x in range(1, len(words))]
    arcs = []
    for trans in [(SH, "_"), (LA, "det"), (SH, "_"), (LA, "nsubj"), (SH, "_"), (SH, "_"), (SH, "_"), (LA, "det"), (LA, "case"), (RA, "nmod"), (RE, "_"), (RA, "nmod")]:
        stack, buffer, arcs = transition(trans, stack, buffer, arcs)
    attach_orphans(arcs, len(words))
    print_tree(0, arcs, words, "")

if __name__ == "__main__":
    parse()
