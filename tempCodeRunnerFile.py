import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


questions = [

    # 1. Valid Anagram - LeetCode #242
    {
        "id": "valid_anagram_242",
        "skill": "Strings & Hashing",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Frontend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 2,
        "title": "Valid Anagram",
        "prompt": (
            "Given two strings s and t, return true if t is an anagram "
            "of s, and false otherwise."
        ),
        "function_name": "is_anagram",
        "function_signature": "def is_anagram(s: str, t: str) -> bool:",
        "starter_code": """def is_anagram(s, t):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": ["anagram", "nagaram"],
                "expected_output": True
            },
            {
                "input_args": ["rat", "car"],
                "expected_output": False
            },
            {
                "input_args": ["listen", "silent"],
                "expected_output": True
            },
            {
                "input_args": ["hello", "world"],
                "expected_output": False,
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "hash map",
            "frequency counting",
            "strings"
        ]
    },


    # 2. Set Matrix Zeroes - LeetCode #73
    {
        "id": "set_matrix_zeroes_73",
        "skill": "Arrays & Matrix",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 3,
        "title": "Set Matrix Zeroes",
        "prompt": (
            "Given an m x n integer matrix, if an element is 0, set its "
            "entire row and column to 0. You must do this in-place."
        ),
        "function_name": "set_zeroes",
        "function_signature": "def set_zeroes(matrix: list[list[int]]) -> None:",
        "starter_code": """def set_zeroes(matrix):
    # modify matrix in-place
    pass""",
        "test_cases": [
            {
                "input_args": [[[1, 1, 1], [1, 0, 1], [1, 1, 1]]],
                "expected_output": [
                    [1, 0, 1],
                    [0, 0, 0],
                    [1, 0, 1]
                ]
            },
            {
                "input_args": [[[0, 1, 2, 0], [3, 4, 5, 2], [1, 3, 1, 5]]],
                "expected_output": [
                    [0, 0, 0, 0],
                    [0, 4, 5, 0],
                    [0, 3, 1, 0]
                ]
            },
            {
                "input_args": [[[1, 2], [3, 4]]],
                "expected_output": [
                    [1, 2],
                    [3, 4]
                ],
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "matrix",
            "in-place manipulation",
            "constant space"
        ]
    },


    # 3. Group Anagrams - LeetCode #49
    {
        "id": "group_anagrams_49",
        "skill": "Arrays & Hashing",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 2,
        "title": "Group Anagrams",
        "prompt": (
            "Given an array of strings strs, group the anagrams together. "
            "You can return the answer in any order."
        ),
        "function_name": "group_anagrams",
        "function_signature": "def group_anagrams(strs: list[str]) -> list[list[str]]:",
        "starter_code": """def group_anagrams(strs):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [["eat", "tea", "tan", "ate", "nat", "bat"]],
                "expected_output": [
                    ["eat", "tea", "ate"],
                    ["tan", "nat"],
                    ["bat"]
                ]
            },
            {
                "input_args": [[""]],
                "expected_output": [[""]]
            },
            {
                "input_args": [["a"]],
                "expected_output": [["a"]]
            },
            {
                "input_args": [["abc", "bca", "cab", "xyz"]],
                "expected_output": [
                    ["abc", "bca", "cab"],
                    ["xyz"]
                ],
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "hash map",
            "sorting",
            "strings"
        ]
    },


    # 4. Remove Nth Node From End of List - LeetCode #19
    {
        "id": "remove_nth_node_19",
        "skill": "Linked Lists",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer"
        ],
        "difficulty": 2,
        "title": "Remove Nth Node From End of List",
        "prompt": (
            "Given the head of a linked list, remove the nth node from "
            "the end of the list and return its head."
        ),
        "function_name": "remove_nth_from_end",
        "function_signature": "def remove_nth_from_end(head: list, n: int) -> list:",
        "starter_code": """def remove_nth_from_end(head, n):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [[1, 2, 3, 4, 5], 2],
                "expected_output": [1, 2, 3, 5]
            },
            {
                "input_args": [[1], 1],
                "expected_output": []
            },
            {
                "input_args": [[1, 2], 1],
                "expected_output": [1]
            },
            {
                "input_args": [[1, 2], 2],
                "expected_output": [2],
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "linked list",
            "two pointers",
            "fast and slow pointers"
        ]
    },


    # 5. LRU Cache - LeetCode #146
    {
        "id": "lru_cache_146",
        "skill": "Design & Data Structures",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "System Design & Distributed Systems"
        ],
        "difficulty": 4,
        "title": "LRU Cache",
        "prompt": (
            "Design a data structure that follows the constraints of a "
            "Least Recently Used cache. Implement get and put operations "
            "in O(1) average time."
        ),
        "function_name": "LRUCache",
        "function_signature": "class LRUCache:",
        "starter_code": """class LRUCache:
    def __init__(self, capacity):
        # your code here
        pass

    def get(self, key):
        pass

    def put(self, key, value):
        pass""",
        "test_cases": [
            {
                "input_args": [
                    2,
                    [
                        ["put", 1, 1],
                        ["put", 2, 2],
                        ["get", 1],
                        ["put", 3, 3],
                        ["get", 2],
                        ["put", 4, 4],
                        ["get", 1],
                        ["get", 3],
                        ["get", 4]
                    ]
                ],
                "expected_output": [
                    None, None, 1, None, -1,
                    None, -1, 3, 4
                ]
            },
            {
                "input_args": [
                    2,
                    [
                        ["put", 1, 10],
                        ["put", 2, 20],
                        ["get", 1],
                        ["put", 3, 30],
                        ["get", 2]
                    ]
                ],
                "expected_output": [
                    None, None, 10, None, -1
                ]
            }
        ],
        "expected_concepts": [
            "hash map",
            "doubly linked list",
            "O(1) operations",
            "LRU"
        ]
    },


    # 6. Lowest Common Ancestor of a BST - LeetCode #235
    {
        "id": "lca_bst_235",
        "skill": "Trees & BST",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 2,
        "title": "Lowest Common Ancestor of a BST",
        "prompt": (
            "Given a binary search tree, find the lowest common ancestor "
            "of two given nodes in the BST."
        ),
        "function_name": "lowest_common_ancestor",
        "function_signature": "def lowest_common_ancestor(root, p, q):",
        "starter_code": """def lowest_common_ancestor(root, p, q):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [
                    [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5],
                    2,
                    8
                ],
                "expected_output": 6
            },
            {
                "input_args": [
                    [6, 2, 8, 0, 4, 7, 9, None, None, 3, 5],
                    2,
                    4
                ],
                "expected_output": 2
            },
            {
                "input_args": [[2, 1, 3], 1, 3],
                "expected_output": 2,
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "binary search tree",
            "tree traversal",
            "recursion"
        ]
    },


    # 7. Diameter of Binary Tree - LeetCode #543
    {
        "id": "diameter_binary_tree_543",
        "skill": "Trees",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 3,
        "title": "Diameter of Binary Tree",
        "prompt": (
            "Given the root of a binary tree, return the length of the "
            "diameter of the tree. The diameter is the longest path between "
            "any two nodes and may or may not pass through the root."
        ),
        "function_name": "diameter_of_binary_tree",
        "function_signature": "def diameter_of_binary_tree(root) -> int:",
        "starter_code": """def diameter_of_binary_tree(root):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [[1, 2, 3, 4, 5]],
                "expected_output": 3
            },
            {
                "input_args": [[1, 2]],
                "expected_output": 1
            },
            {
                "input_args": [[1]],
                "expected_output": 0
            },
            {
                "input_args": [[1, 2, 3, 4, 5, 6, 7]],
                "expected_output": 4,
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "binary tree",
            "DFS",
            "recursion",
            "tree height"
        ]
    },


    # 8. Clone Graph - LeetCode #133
    {
        "id": "clone_graph_133",
        "skill": "Graphs",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 3,
        "title": "Clone Graph",
        "prompt": (
            "Given a reference of a node in a connected undirected graph, "
            "return a deep copy of the graph."
        ),
        "function_name": "clone_graph",
        "function_signature": "def clone_graph(node):",
        "starter_code": """def clone_graph(node):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [
                    [[2, 4], [1, 3], [2, 4], [1, 3]]
                ],
                "expected_output": [
                    [2, 4], [1, 3], [2, 4], [1, 3]
                ]
            },
            {
                "input_args": [
                    [[2], [1]]
                ],
                "expected_output": [
                    [2], [1]
                ]
            },
            {
                "input_args": [[]],
                "expected_output": [],
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "graph",
            "DFS",
            "BFS",
            "hash map"
        ]
    },


    # 9. Pacific Atlantic Water Flow - LeetCode #417
    {
        "id": "pacific_atlantic_417",
        "skill": "Graphs & Matrix",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 3,
        "title": "Pacific Atlantic Water Flow",
        "prompt": (
            "Given an m x n matrix of heights, return a list of grid "
            "coordinates where water can flow to both the Pacific and "
            "Atlantic oceans."
        ),
        "function_name": "pacific_atlantic",
        "function_signature": "def pacific_atlantic(heights: list[list[int]]) -> list[list[int]]:",
        "starter_code": """def pacific_atlantic(heights):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [
                    [
                        [1, 2, 2, 3, 5],
                        [3, 2, 3, 4, 4],
                        [2, 4, 5, 3, 1],
                        [6, 7, 1, 4, 5],
                        [5, 1, 1, 2, 4]
                    ]
                ],
                "expected_output": [
                    [0, 4],
                    [1, 3],
                    [1, 4],
                    [2, 2],
                    [3, 0],
                    [3, 1],
                    [4, 0]
                ]
            },
            {
                "input_args": [[[1]]],
                "expected_output": [[0, 0]]
            },
            {
                "input_args": [
                    [[1, 2], [3, 4]]
                ],
                "expected_output": [
                    [0, 1],
                    [1, 0],
                    [1, 1]
                ],
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "DFS",
            "BFS",
            "matrix",
            "graph traversal"
        ]
    },


    # 10. Coin Change - LeetCode #322
    {
        "id": "coin_change_322",
        "skill": "Dynamic Programming",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 3,
        "title": "Coin Change",
        "prompt": (
            "You are given an integer array coins representing coins of "
            "different denominations and an integer amount. Return the "
            "fewest number of coins that you need to make up that amount. "
            "If the amount cannot be made up, return -1."
        ),
        "function_name": "coin_change",
        "function_signature": "def coin_change(coins: list[int], amount: int) -> int:",
        "starter_code": """def coin_change(coins, amount):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [[1, 2, 5], 11],
                "expected_output": 3
            },
            {
                "input_args": [[2], 3],
                "expected_output": -1
            },
            {
                "input_args": [[1], 0],
                "expected_output": 0
            },
            {
                "input_args": [[2, 5, 10, 1, 3], 27],
                "expected_output": 4,
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "dynamic programming",
            "bottom-up DP",
            "unbounded knapsack"
        ]
    },


    # 11. Partition Equal Subset Sum - LeetCode #416
    {
        "id": "partition_equal_subset_sum_416",
        "skill": "Dynamic Programming",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 3,
        "title": "Partition Equal Subset Sum",
        "prompt": (
            "Given an integer array nums, return true if you can partition "
            "the array into two subsets such that the sum of the elements "
            "in both subsets is equal."
        ),
        "function_name": "can_partition",
        "function_signature": "def can_partition(nums: list[int]) -> bool:",
        "starter_code": """def can_partition(nums):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [[1, 5, 11, 5]],
                "expected_output": True
            },
            {
                "input_args": [[1, 2, 3, 5]],
                "expected_output": False
            },
            {
                "input_args": [[2, 2, 3, 5]],
                "expected_output": False
            },
            {
                "input_args": [[2, 2, 2, 2]],
                "expected_output": True,
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "dynamic programming",
            "0/1 knapsack",
            "subset sum"
        ]
    },


    # 12. Permutations - LeetCode #46
    {
        "id": "permutations_46",
        "skill": "Backtracking",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 3,
        "title": "Permutations",
        "prompt": (
            "Given an array nums of distinct integers, return all the "
            "possible permutations. You can return the answer in any order."
        ),
        "function_name": "permute",
        "function_signature": "def permute(nums: list[int]) -> list[list[int]]:",
        "starter_code": """def permute(nums):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [[1, 2, 3]],
                "expected_output": [
                    [1, 2, 3],
                    [1, 3, 2],
                    [2, 1, 3],
                    [2, 3, 1],
                    [3, 1, 2],
                    [3, 2, 1]
                ]
            },
            {
                "input_args": [[0, 1]],
                "expected_output": [
                    [0, 1],
                    [1, 0]
                ]
            },
            {
                "input_args": [[1]],
                "expected_output": [[1]]
            }
        ],
        "expected_concepts": [
            "backtracking",
            "recursion",
            "permutations"
        ]
    },


    # 13. Find Median from Data Stream - LeetCode #295
    {
        "id": "median_data_stream_295",
        "skill": "Heaps & Data Structures",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Data Scientist",
            "System Design & Distributed Systems"
        ],
        "difficulty": 4,
        "title": "Find Median from Data Stream",
        "prompt": (
            "Design a data structure that supports adding integers from "
            "a data stream and finding the median of all elements added "
            "so far."
        ),
        "function_name": "MedianFinder",
        "function_signature": "class MedianFinder:",
        "starter_code": """class MedianFinder:
    def __init__(self):
        # your code here
        pass

    def addNum(self, num):
        pass

    def findMedian(self):
        pass""",
        "test_cases": [
            {
                "input_args": [
                    ["addNum", 1],
                    ["addNum", 2],
                    ["findMedian"]
                ],
                "expected_output": [
                    None,
                    None,
                    1.5
                ]
            },
            {
                "input_args": [
                    ["addNum", 1],
                    ["addNum", 2],
                    ["addNum", 3],
                    ["findMedian"]
                ],
                "expected_output": [
                    None,
                    None,
                    None,
                    2
                ]
            },
            {
                "input_args": [
                    ["addNum", 5],
                    ["addNum", 3],
                    ["findMedian"],
                    ["addNum", 8],
                    ["addNum", 9],
                    ["findMedian"]
                ],
                "expected_output": [
                    None,
                    None,
                    4,
                    None,
                    None,
                    6.5
                ]
            }
        ],
        "expected_concepts": [
            "heap",
            "two heaps",
            "priority queue",
            "data stream"
        ]
    },


    # 14. Product of Array Except Self - LeetCode #238
    {
        "id": "product_array_except_self_238",
        "skill": "Arrays",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Frontend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 2,
        "title": "Product of Array Except Self",
        "prompt": (
            "Given an integer array nums, return an array answer such that "
            "answer[i] is equal to the product of all the elements of nums "
            "except nums[i]. You must solve it without using division and "
            "in O(n) time."
        ),
        "function_name": "product_except_self",
        "function_signature": "def product_except_self(nums: list[int]) -> list[int]:",
        "starter_code": """def product_except_self(nums):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [[1, 2, 3, 4]],
                "expected_output": [24, 12, 8, 6]
            },
            {
                "input_args": [[-1, 1, 0, -3, 3]],
                "expected_output": [0, 0, 9, 0, 0]
            },
            {
                "input_args": [[2, 3, 4, 5]],
                "expected_output": [60, 40, 30, 24]
            },
            {
                "input_args": [[1, 0, 3, 0]],
                "expected_output": [0, 0, 0, 0],
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "arrays",
            "prefix product",
            "suffix product",
            "O(n) time",
            "O(1) extra space"
        ]
    },


    # 15. Majority Element - LeetCode #169
    {
        "id": "majority_element_169",
        "skill": "Arrays & Hashing",
        "role_tags": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
            "Data Scientist"
        ],
        "difficulty": 2,
        "title": "Majority Element",
        "prompt": (
            "Given an array nums of size n, return the majority element. "
            "The majority element is the element that appears more than "
            "floor(n / 2) times. You may assume that the majority element "
            "always exists in the array."
        ),
        "function_name": "majority_element",
        "function_signature": "def majority_element(nums: list[int]) -> int:",
        "starter_code": """def majority_element(nums):
    # your code here
    pass""",
        "test_cases": [
            {
                "input_args": [[3, 2, 3]],
                "expected_output": 3
            },
            {
                "input_args": [[2, 2, 1, 1, 1, 2, 2]],
                "expected_output": 2
            },
            {
                "input_args": [[3, 3, 4]],
                "expected_output": 3,
                "is_hidden": True
            },
            {
                "input_args": [[1, 1, 1, 2, 2]],
                "expected_output": 1,
                "is_hidden": True
            }
        ],
        "expected_concepts": [
            "arrays",
            "hash map",
            "Boyer-Moore Voting Algorithm",
            "O(n) time",
            "O(1) space"
        ]
    }
]


def insert_questions():
    try:
        response = (
            supabase
            .table("coding_questions")
            .insert(questions)
            .execute()
        )

        print("Questions inserted successfully!")

        for question in response.data:
            print(f"Inserted: {question['id']}")

    except Exception as e:
        print("Error inserting questions:")
        print(e)


insert_questions()