# encoding: utf-8

from nltk.corpus import wordnet as wn
from itertools import combinations, chain
import re
import spacy
from langdetect import detect

# https://stackoverflow.com/questions/39763091/how-to-extract-subjects-in-a-sentence-and-their-respective-dependent-phrases
# https://github.com/krzysiekfonal/textpipeliner
class CohesionAnalyzerEnglish:

    def __init__(self, text):
        # Get language of text
        language = detect(text.decode('utf-8'))

        # English text
        if language == 'en':
            # Load spacy
            self.nlp = spacy.load('en')
        # German text
        elif language == 'de':
            # Load spacy
            self.nlp = spacy.load('de')

        # Prepare text and remove unwanted characters
        self.text = self.nlp(text.decode('utf-8'))

        # Extract sentences
        self.sents = [sent for sent in self.text.sents]

        # Word pairs
        self.word_pairs = self._generate_nouns() + self._generate_hyponyms_hyperonyms()

        # All concepts
        self.concepts = list(set([pair['source'] for pair in self.word_pairs] + \
                       [pair['target'] for pair in self.word_pairs]))

    def _generate_nouns(self):
        """Filter all nouns from sentences and
        return list of sentences with nouns"""

        word_pairs = []

        for sentence in self.sents:

            # Get root from sentence
            root = [w for w in sentence if w.head is w][0]

            # Get subject
            subject = list(root.lefts)[0]

            # Extract nouns from sentence
            nouns = [word for word in sentence if any(word.pos_ in s for s in ["PROPN", "NOUN"])]

            # Subject is a noun
            if any(subject.pos_ in s for s in ["NOUN", "PROPN"]):
                # Build word pairs
                for noun in nouns:
                    # Subject should not be the noun
                    if noun.lemma_ != subject.lemma_:
                        # Append word pair
                        word_pairs.append({'source': subject.lemma_, 'target': noun.lemma_})
            # There is no subject in the sentence
            else:
                # Generate all combinations
                combs = combinations(nouns, 2)

                # Loop over every combination
                for comb in combs:
                    word_pairs.append({'source': comb[0].lemma_, 'target': comb[1].lemma_})

        return word_pairs


    def _generate_hyponyms_hyperonyms(self):
        """Generates a word pair list of hyperonyms and
        hyponyms from a given dataset"""

        word_pairs = []

        # Loop over every sentence
        for index, sentence in enumerate(self.sents):
            # Do not loop over last sentence
            if index < (len(self.sents) - 1):

                # Get all nouns from current and next sentence
                nouns_current_sentence = [noun.lemma_ for noun in sentence if any(noun.pos_ in s for s in ['PROPN', 'NOUN'])]
                nouns_next_sentence = [noun.lemma_ for noun in self.sents[index + 1] if any(noun.pos_ in s for s in ['PROPN', 'NOUN'])]

                # Loop over every noun in current sentence
                for noun in nouns_current_sentence:
                    ###############################
                    # Get hypernyms and hyponyms
                    ###############################
                    # Get all synsets of current noun
                    synsets_current_noun = [synset for synset in wn.synsets(noun)]

                    # Get all hyponyms and hyperonyms from all synsets
                    hyponyms_current_noun = [synset.hyponyms() for synset in synsets_current_noun]
                    hypernyms_current_noun = [synset.hypernyms() for synset in synsets_current_noun]

                    # Get all synsets of hyperonyms and hypernyms
                    synsets = [synset for synsets in (hyponyms_current_noun + hypernyms_current_noun) for synset in synsets]

                    # Get all lemmas
                    hypernyms_hyponyms = ([lemma.name().replace('_', ' ') for synset in synsets for lemma in synset.lemmas()])

                    ################################
                    # Connect to next sentence
                    ################################
                    # sentences_share_element = bool(set(hypernyms_hyponyms) & set(nouns_next_sentence))
                    sentences_shared_elements = list(set(hypernyms_hyponyms).intersection(nouns_next_sentence))

                    if len(sentences_shared_elements) > 0:
                        # print(sentences_share_element)
                        for shared_element in sentences_shared_elements:
                            word_pairs.append({'source': noun, 'target': shared_element})

        return word_pairs


    def _calculate_number_relations(self):
        """Calculates the number of relations"""

        # Make tuples from word_pairs
        tuples = map(lambda x: (x['source'], x['target']), self.word_pairs)

        # Remove duplicates
        tuples = list(set([(pair[0], pair[1])
            for pair in tuples if pair[0] != pair[1]]))

        return len(tuples)


    def _get_clusters(self):
        """Calculates the number of computed
        clusters"""

        # If we only have one sentence return word pairs
        # as single cluster
        if len(self.sents) == 1:
            return self.word_pairs

        # Initialize clusters. The cluster
        # later stores all clusters as a list containing
        # the word pair dictionaries
        clusters = []

        # Store all words that have already been
        # assigned to a cluster
        assigned_words = []

        # Loop over every word pair
        for num in range(0, len(self.word_pairs)):
            # Store all words that are stored in the current cluster
            current_word_pair = [self.word_pairs[num]['source'],
                    self.word_pairs[num]['target']]

            # Only assign a new cluster if the current word pair has
            # not already been processed
            if (not bool(set(current_word_pair) & set(assigned_words))):
                # Init current cluster
                current_cluster = [self.word_pairs[num]]

                # Remember that we already added the words of the current cluster
                assigned_words.append(current_word_pair[0])
                assigned_words.append(current_word_pair[1])

                # Index of word_pair we already added to current cluster.
                # We store the index to reduce the computation. If we already
                # added an index to the current cluster, there is no need
                # to look at it again
                index_pairs_added = [num]

                # Found set to true for while loop
                found = True

                # As long as we still find connections keep on looping
                while found:
                    # Found set to false
                    found = False

                    # Loop over every word pair again
                    for num_again in range(0, len(self.word_pairs)):
                        # Word pairs do not match
                        if num_again not in index_pairs_added:
                            # Store both words of current pair in list
                            iter_word_pair = [self.word_pairs[num_again]['source'],
                                    self. word_pairs[num_again]['target']]

                            # Lemmas in current cluster
                            current_cluster_lemma_source = map(lambda x: x['source'], current_cluster)
                            current_cluster_lemma_target = map(lambda x: x['target'], current_cluster)

                            # Get all words in current cluster
                            current_cluster_lemma = current_cluster_lemma_source + \
                                        current_cluster_lemma_target

                            # Both pairs share an element
                            shared_element = bool(set(current_cluster_lemma) & set(iter_word_pair))

                            # If they share an element append to current cluster
                            if shared_element:
                                # Append pair to current cluster
                                current_cluster.append(self.word_pairs[num_again])

                                # Remember that we already appended this
                                # pair to the current cluster
                                index_pairs_added.append(num_again)

                                # Add word pair that belongs to current cluster
                                # to list of assigned word pairs. By doing this
                                # we know if a word has already been assigned
                                # to a cluster.
                                assigned_words.append(iter_word_pair[0])
                                assigned_words.append(iter_word_pair[1])

                                # We found a candidate. When we found a connection
                                # a new word might be added to the current
                                # cluster. Therefore we have too loop over
                                # every word pair again to see if we
                                # missed a connection with the new word
                                found = True

                # Append current cluster to all clusters
                clusters.append(current_cluster)

        return clusters


    def _get_word_cluster_index(self, cluster):
        """Generate a dictionary that
        has the words as key and the cluster number
        as value"""

        # When clusters are calculated assign them to the word_pairs as
        # an additional value
        word_cluster_index = {}

        # Loop over every cluster
        for index, single_cluster in enumerate(cluster):
            # Get words for current cluster
            source_words = map(lambda x: x['source'], single_cluster)
            target_words = map(lambda x: x['target'], single_cluster)

            # Concatenate sources and targets in to one array
            words = source_words + target_words

            # Assign index to word_cluster_index dict
            for word in words:
                word_cluster_index[word] = index

        return word_cluster_index


    def get_data_for_visualization(self):
        """Get all data for get_data for visualization"""

        # Get clusters
        cluster = self._get_clusters()

        # Create dictionary of words and it's corresponding clusters
        word_cluster_index = self._get_word_cluster_index(cluster)

        # Get unique nodes
        nodes = map(lambda x: [x['source'], x['target']], self.word_pairs)
        nodes = list(set(list(chain(*nodes))))
        nodes = [{'id': word, 'index': ind} for ind, word, in enumerate(nodes)]


        return {'links': self.word_pairs,
                'nodes': nodes,
                'numRelations': self._calculate_number_relations(),
                'numSentences': len(self.sents),
                'numConcepts': len(self.concepts),
                'clusters': cluster,
                'numCluster': len(cluster)}


model = CohesionAnalyzerEnglish("""
    John Grisham graduated from Mississippi State University before attending the University of Mississippi School of Law in 1981.
    He practiced criminal law for about a decade and served in the House of Representatives in Mississippi from January 1984 to September 1990.
    His first novel, A Time to Kill, was published in June 1989, four years after he began writing it.
    As of 2012, his books and novellas have sold over 275 million copies worldwide.
    A Galaxy British Book Awards winner, Grisham is one of only three authors to sell 2 million copies on a first printing.
    Michael went into the pool.""")

# text3 = """Das Wissen zeichnet einen Menschen aus. Sprachkenntnis zum
#     Beispiel ist wichtig, da Menschen sonst nicht Sprechen koennen. Der Bezug
#     zur Realitt ermglicht dies. Vor allem der Praxisbezug ist dabei wichtig.
#     """

print(model.get_data_for_visualization())
# print(model2.get_data_for_visualization())

