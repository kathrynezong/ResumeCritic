#!/usr/bin/env python3
"""
Test Semantic Similarity Performance
Run: python test_semantic_similarity.py
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded!\n")

# Test cases: (text1, text2, expected_similarity)
test_cases = [
    # High similarity - synonyms
    ("Machine Learning Engineer", "ML Engineer", "HIGH"),
    ("Python developer", "Python programmer", "HIGH"),
    ("Data Scientist", "Data Analyst", "HIGH"),
    ("Frontend developer", "Front-end engineer", "HIGH"),
    
    # Medium similarity - related concepts
    ("Python developer", "Java developer", "MEDIUM"),
    ("Machine Learning", "Artificial Intelligence", "MEDIUM"),
    ("DevOps Engineer", "Software Engineer", "MEDIUM"),
    
    # Low similarity - unrelated
    ("Python developer", "Cat lover", "LOW"),
    ("Machine Learning", "Cooking recipes", "LOW"),
    ("Software Engineer", "Medical Doctor", "LOW"),
    
    # Resume matching examples
    ("5 years Python Django experience", "Python Django developer needed", "HIGH"),
    ("Built ML models with TensorFlow", "Experience with machine learning and deep learning", "HIGH"),
    ("React and Node.js full stack", "Frontend React developer", "MEDIUM"),
    ("Marketing manager social media", "Software engineer Python", "LOW"),
]

print("=" * 80)
print("SEMANTIC SIMILARITY TEST RESULTS")
print("=" * 80)

correct = 0
total = len(test_cases)

for text1, text2, expected in test_cases:
    # Compute similarity
    embeddings = model.encode([text1, text2])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    
    # Classify result
    if similarity > 0.7:
        result = "HIGH"
    elif similarity > 0.4:
        result = "MEDIUM"
    else:
        result = "LOW"
    
    # Check if correct
    is_correct = (result == expected)
    correct += is_correct
    
    # Print result
    status = "✓" if is_correct else "✗"
    print(f"\n{status} Score: {similarity:.3f} ({result}) - Expected: {expected}")
    print(f"  '{text1}'")
    print(f"  '{text2}'")

print("\n" + "=" * 80)
print(f"ACCURACY: {correct}/{total} ({100*correct/total:.1f}%)")
print("=" * 80)

# Additional insights
print("\n\nKEY INSIGHTS:")
print("-" * 80)
print("• Scores > 0.7: Very similar (synonyms, same concept)")
print("• Scores 0.4-0.7: Somewhat related (same domain)")
print("• Scores < 0.4: Not related")
print("\nThis is why semantic similarity is better than keyword matching!")
