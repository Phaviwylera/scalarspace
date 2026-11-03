import unittest

import secp256k1_scalar_sim as sim


class ScalarDomainTests(unittest.TestCase):
    def setUp(self):
        self.space = sim.Secp256k1ScalarSpace()

    def test_raw_256_bit_space_and_valid_scalar_domain_are_distinct(self):
        raw_count = 1 << 256
        self.assertEqual(self.space.size, sim.N - 1)
        self.assertEqual(raw_count - self.space.size, 432420386565659656852420866394968145600)
        self.assertFalse(self.space.contains(0))
        self.assertTrue(self.space.contains(1))
        self.assertTrue(self.space.contains(sim.N - 1))
        self.assertFalse(self.space.contains(sim.N))
        self.assertFalse(self.space.contains((1 << 256) - 1))
        self.assertFalse(self.space.contains(True))

    def test_balanced_partitions_are_gap_free_for_several_sizes(self):
        for parts in (1, 2, 3, 7, 16, 97, 1000):
            with self.subTest(parts=parts):
                self.assertTrue(self.space.verify_partition(parts))
                intervals = list(self.space.partitions(parts))
                self.assertEqual(intervals[0].start, 1)
                self.assertEqual(intervals[-1].stop, sim.N)
                self.assertEqual(sum(item.count for item in intervals), self.space.size)
                self.assertLessEqual(
                    max(item.count for item in intervals) - min(item.count for item in intervals),
                    1,
                )

    def test_locate_matches_every_partition_edge(self):
        parts = 97
        for index in range(parts):
            interval = self.space.interval(index, parts)
            self.assertEqual(self.space.locate(interval.start, parts), index)
            self.assertEqual(self.space.locate(interval.stop - 1, parts), index)

    def test_known_generator_multiples(self):
        two_g = (
            int("c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5", 16),
            int("1ae168fea63dc339a3c58419466ceaeef7f632653266d0e1236431a950cfe52a", 16),
        )
        self.assertEqual(sim.scalar_multiply(1), sim.G)
        self.assertEqual(sim.scalar_multiply(2), two_g)
        self.assertTrue(sim.is_on_curve(sim.scalar_multiply(3)))
        self.assertEqual(sim.scalar_multiply(sim.N), None)
        self.assertEqual(sim.scalar_multiply(sim.N + 1), sim.G)

    def test_negative_generator_encoding(self):
        negative_g = (sim.GX, (-sim.GY) % sim.P)
        self.assertEqual(sim.scalar_multiply(sim.N - 1), negative_g)
        self.assertTrue(sim.is_on_curve(negative_g))
        self.assertEqual(sim.encode_public_point(negative_g, compressed=True)[:2], "03")

    def test_scalar_multiply_rejects_negative_and_non_integer_inputs(self):
        with self.assertRaises(ValueError):
            sim.scalar_multiply(-1)
        with self.assertRaises(TypeError):
            sim.scalar_multiply(True)

    def test_point_encoding_matches_sec1_vectors(self):
        self.assertEqual(
            sim.encode_public_point(sim.G),
            "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798",
        )
        encoded = sim.encode_public_point(sim.G, compressed=False)
        self.assertEqual(len(encoded), 130)
        self.assertTrue(encoded.startswith("04"))
        with self.assertRaises(ValueError):
            sim.encode_public_point(None)

    def test_manifest_integrity_and_exact_plan_validation(self):
        manifest = sim.create_manifest(parts=17, workers=4)
        valid, _ = sim.validate_manifest(manifest)
        self.assertTrue(valid)
        manifest["partitions"][0]["worker_id"] = 3
        valid, _ = sim.validate_manifest(manifest)
        self.assertFalse(valid)

    def test_coverage_is_exact_bookkeeping_and_rejects_bad_indexes(self):
        manifest = sim.create_manifest(parts=17, workers=4)
        report = sim.coverage_report(manifest, [0, 1, 2, 3, 4])
        expected = sum(int(manifest["partitions"][i]["count_decimal"]) for i in range(5))
        self.assertEqual(int(report["covered_scalar_count_decimal"]), expected)
        self.assertEqual(report["remaining_partition_count"], 12)
        self.assertIn("does not measure candidate computations", report["metric"])
        with self.assertRaises(ValueError):
            sim.coverage_report(manifest, [17])

    def test_exact_analysis_totals_match_domain(self):
        analysis = sim.exact_analysis(parts=23, workers=5, bins=16)
        self.assertEqual(
            sum(int(row["scalar_count_decimal"]) for row in analysis["worker_analysis"]),
            self.space.size,
        )
        self.assertEqual(
            sum(int(row["scalar_count_decimal"]) for row in analysis["equal_as_possible_bins"]),
            self.space.size,
        )
        self.assertTrue(analysis["partition_analysis"]["exact_gap_free_coverage"])

    def test_full_self_verification_passes(self):
        self.assertTrue(sim.verify_implementation()["all_pass"])


if __name__ == "__main__":
    unittest.main()
