SYNTHETIC VISUAL-SIMILARITY DEMO DATASET
============================================

50 fictional adult identities with synthetic portrait images.

Files:
- P001.jpg ... P050.jpg : individual portrait images
- people.csv             : metadata for MySQL import
- people.sql             : CREATE TABLE + INSERT statements
- source_grid.png        : original 50-person labeled composite

Suggested classroom architecture:
image upload -> image embedding -> vector search -> MySQL metadata -> LLM report

IMPORTANT:
These are synthetic/fictional demo identities. The similarity score from an
embedding model should be presented as a visual similarity measure, not as
proof of identity or a probability of identity.
