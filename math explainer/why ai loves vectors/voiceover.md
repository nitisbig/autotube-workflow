[curious] Imagine I ask an AI this question:

“What is the capital of France?”

[pause]

[thoughtful] To you, these are words.

But to a computer, the words “capital,” “France,” and even the question itself cannot exist as language.

Computers understand numbers.

[pause]

So somewhere inside an AI system, this sentence has to become mathematics.

[building curiosity] And one of the most important mathematical objects making that possible is surprisingly simple:

[emphasis] a vector.

[pause]

[curious] So what exactly is a vector?

You may remember vectors from physics.

An arrow pointing in some direction.

For example, this vector might move three units to the right and two units upward.

We can write it as two numbers:

[slowly] three... two.

The first number tells us how far to move horizontally.

The second tells us how far to move vertically.

[pause]

[thoughtful] But there is another way to think about a vector.

[emphasis] A vector is simply a list of numbers.

Three, two.

Or perhaps:

three, two, five.

Or a thousand different numbers.

[pause]

[building excitement] And this simple idea gives artificial intelligence something extremely powerful:

[emphasis] a way to turn meaning into geometry.

[pause]

Let's start with a tiny example.

Suppose we have three words:

cat,

dog,

and car.

We want a computer to somehow understand that “cat” and “dog” are related, while “car” is very different.

[pause]

Imagine giving each word two numerical properties.

The first represents how much the object is related to animals.

The second represents how much it is related to machines.

A cat might become:

0.9, 0.1.

A dog might become:

0.85, 0.1.

And a car might become:

0.05, 0.95.

[pause]

[curious] Now place these vectors on a graph.

Something interesting happens.

Cat and dog appear close together.

Car appears somewhere else.

[pause]

[emphasis] We have taken something abstract — meaning — and turned it into distance.

This is the basic intuition behind something called an embedding.

[clear] An embedding represents information as vectors.

[pause]

Real AI systems don't use just two dimensions.

They might use hundreds or thousands.

So instead of representing the word “cat” with two numbers, it might look something like:

[measured] 0.17...

negative 0.42...

0.81...

0.06...

and hundreds of other values.

[pause]

[thoughtful] Individually, these numbers usually don't have simple meanings like “animal” or “machine.”

But together, their position captures useful patterns.

[pause]

[building curiosity] And this is where vectors become fascinating.

Suppose two vectors point in similar directions.

Mathematically, we can measure their similarity using something called the dot product.

Take two vectors.

Multiply their matching components.

Then add the results.

[pause]

If the vectors point in similar directions, the dot product tends to be large.

If they point in very different directions, it tends to be smaller.

[emphasis] AI systems can use ideas like this to compare pieces of information.

[pause]

So when you type:

“The cat chased the mouse,”

the model doesn't see words floating in empty space.

[thoughtful] It works with numerical representations that can be compared, transformed, and combined.

[pause]

But vectors aren't limited to words.

[slightly excited] An image can become vectors too.

Imagine an image of a dog.

At first, the image is just pixels.

Every pixel contains numbers describing brightness and color.

A neural network processes those numbers through layer after layer.

[pause]

Early layers might respond to simple features:

edges,

lines,

corners.

Later layers can represent more complex patterns:

eyes,

ears,

fur,

faces,

objects.

[pause]

Eventually, the image becomes an internal vector representation.

[building excitement] So an image of a dog and the word “dog” can both be represented mathematically.

This is what makes systems that connect text and images possible.

[emphasis] Vectors give different kinds of information a common mathematical language.

[pause]

And there's another reason AI loves vectors.

Computers are incredibly good at performing operations on large arrays of numbers.

Suppose we have one vector.

We can multiply it by another mathematical object called a matrix.

[pause]

A matrix can rotate a vector,

stretch it,

compress it,

or transform it into a completely different space.

Inside a neural network, this happens constantly.

[ rhythmic ] Vector goes in.

Matrix transformation.

New vector comes out.

Then another transformation.

And another.

And another.

[pause]

[emphasis] What we call a neural network is, at a mathematical level, largely a huge sequence of transformations applied to vectors.

[pause]

Now let's return to language.

Imagine the sentence:

“The animal didn't cross the street because it was tired.”

[pause]

[curious] What does “it” refer to?

Probably the animal.

But how could a machine determine that?

[pause]

Modern language models use a mechanism called attention.

[emphasis] And vectors are at the center of it.

Each word is converted into vectors.

Then the model creates different versions of those vectors, usually called queries, keys, and values.

The model compares them mathematically.

[pause]

If two pieces of information are strongly related, their vectors produce a stronger connection.

So the representation for “it” can pay more attention to “animal” than to “street.”

[pause]

This process happens again and again across many layers.

[building intensity] Millions or billions of vector operations eventually produce the model's understanding of your sentence.

[pause]

Even the output works with vectors.

Suppose the model is trying to predict the next word:

“The sky is…”

[pause]

Inside the model is a vector representing everything it has understood so far.

That vector is transformed into scores for possible next words.

Blue might receive a high score.

Clear might receive another.

Falling might receive a much lower one.

Those scores become probabilities.

One word is selected.

Then the process repeats.

[pause]

[emphasis] So when an AI generates a paragraph, behind every word are enormous numbers of vector calculations.

[pause]

[thoughtful] But perhaps the most surprising thing about vectors is this:

they can capture relationships.

In a good vector space, similar ideas often appear near each other.

Paris may be close to France.

Tokyo may relate similarly to Japan.

Words involving emotions may form patterns.

Programming concepts may form others.

[pause]

The geometry isn't perfect, and it isn't the same as human understanding.

[measured] But it can encode enough structure to make extremely powerful predictions.

[pause]

[thoughtful] This gives us a useful way to think about modern AI.

AI doesn't store knowledge like a dictionary with neat definitions.

Instead, much of what it learns is distributed across enormous mathematical spaces.

[pause]

[slowly] Ideas become patterns.

Relationships become directions.

Similarity becomes distance.

And computation becomes movement through those spaces.

[pause]

[building excitement] This is why vectors appear almost everywhere in machine learning.

Text becomes vectors.

Images become vectors.

Audio becomes vectors.

Videos become vectors.

User preferences can become vectors.

Even entire documents can become vectors.

[pause]

Once something becomes a vector, mathematics can compare it with something else.

Search engines can find similar documents.

Recommendation systems can find similar interests.

Image systems can connect pictures with descriptions.

Language models can connect one word with the context around it.

[pause]

[thoughtful] The vector itself isn't intelligent.

It's just numbers.

[pause]

[building intensity] But when billions of these numerical representations interact through carefully learned mathematical transformations...

something remarkable happens.

[pause]

A machine begins to recognize patterns that look surprisingly close to meaning.

[pause]

[calm] So the next time you ask an AI a question, remember what's happening underneath.

Your words disappear.

They become numbers.

Those numbers become points in enormous mathematical spaces.

Those points are compared, transformed, combined, and passed through layer after layer.

[pause]

[slowly] And eventually...

numbers become language again.

[pause]

[softly] AI may seem like magic.

But deep underneath it...

[pause]

[emphasis] are vectors.