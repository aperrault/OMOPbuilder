import unittest
from AllOfUSMockDB import AllOfUsMockDB

class TestConceptIDExtraction(unittest.TestCase):
    def setUp(self):
        # Initialize DB without loading external files
        self.db = AllOfUsMockDB()
        self.db.vocab_loaded = True # Fake it so checks run

        # Insert Dummy Concepts
        self.db.con.execute("DELETE FROM concept")
        self.db.con.execute("""
            INSERT INTO concept (concept_id, concept_name, domain_id, vocabulary_id, standard_concept, concept_code) VALUES
            (8532, 'FEMALE', 'Gender', 'Gender', 'S', 'F'),
            (201826, 'Type 2 diabetes mellitus', 'Condition', 'SNOMED', 'S', '44054006'),
            (12345, 'Specific T2D Complication', 'Condition', 'SNOMED', 'S', '12345'),
            (999, 'Small ID', 'Misc', 'Misc', 'S', '999')
        """)

        # Insert Dummy Ancestors
        self.db.con.execute("DELETE FROM concept_ancestor")
        self.db.con.execute("""
            INSERT INTO concept_ancestor (ancestor_concept_id, descendant_concept_id, min_levels_of_separation, max_levels_of_separation) VALUES
            (201826, 12345, 1, 1),
            (201826, 201826, 0, 0), -- Self-reference
            (8532, 8532, 0, 0)      -- Self-reference only (Leaf node)
        """)

    def test_ancestor_flagging(self):
        # 201826 has a descendant (12345), so it SHOULD be flagged as [ANCESTOR]
        sql = "SELECT * FROM condition_occurrence WHERE condition_concept_id = 201826"
        report = self.db.check_concept_ids(sql)
        self.assertIn("ID 201826 -> Type 2 diabetes mellitus", report)
        self.assertIn("[ANCESTOR]", report)

        # 8532 has only itself as descendant, so it should NOT be flagged
        sql = "SELECT * FROM person WHERE gender_concept_id = 8532"
        report = self.db.check_concept_ids(sql)
        self.assertIn("ID 8532 -> FEMALE", report)
        self.assertNotIn("[ANCESTOR]", report)

    def test_equality_extraction(self):
        sql = "SELECT * FROM person WHERE gender_concept_id = 8532"
        report = self.db.check_concept_ids(sql)
        
        self.assertIn("ID 8532 -> FEMALE", report)
        self.assertNotIn("Unknown IDs", report)

    def test_in_clause_extraction(self):
        sql = "SELECT * FROM condition_occurrence WHERE condition_concept_id IN (201826, 99999)"
        report = self.db.check_concept_ids(sql)
        
        # 201826 is in DB and is an ancestor
        self.assertIn("ID 201826 -> Type 2 diabetes mellitus", report)
        self.assertIn("[ANCESTOR]", report)
        
        # 99999 is missing
        self.assertIn("Unknown IDs", report)
        self.assertIn("99999", report)

    def test_alias_extraction(self):
        sql = "SELECT 12345 AS condition_concept_id"
        report = self.db.check_concept_ids(sql)
        
        self.assertIn("ID 12345 -> Specific T2D Complication", report)

    def test_ignore_non_concept_columns(self):
        # Should ignore 1980 because column doesn't end in concept_id
        sql = "SELECT * FROM person WHERE year_of_birth = 1980"
        report = self.db.check_concept_ids(sql)
        
        self.assertIn("No Concept IDs found", report)

    def test_ignore_small_numbers_heuristic_removed(self):
        # We removed the heuristic, so if it matches the regex, it should be checked.
        # But wait, did we remove the < 1000 check? 
        # Let's check the code... The user asked to remove heuristics, but I implemented regex based extraction.
        # If I use `concept_id = 999`, it SHOULD be checked now because it matches the pattern.
        
        sql = "SELECT * FROM x WHERE some_concept_id = 999"
        report = self.db.check_concept_ids(sql)
        self.assertIn("ID 999 -> Small ID", report)

if __name__ == '__main__':
    unittest.main()
