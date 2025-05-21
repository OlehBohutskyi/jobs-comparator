import re
import numpy as np
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

def cosine_similarity_word2vec(text1, text2):
    # Попередня обробка тексту
    def preprocess(text):
        # Переведення в нижній регістр і видалення розділових знаків
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    # Обробка текстів
    text1 = preprocess(text1)
    text2 = preprocess(text2)
    
    # Токенізація (розбиття на слова)
    words1 = text1.split()
    words2 = text2.split()
    
    # Об'єднання всіх слів для навчання моделі
    all_sentences = [words1, words2]
    
    # Навчання моделі Word2Vec
    model = Word2Vec(sentences=all_sentences, vector_size=100, window=5, min_count=1, workers=4)
    
    # Отримання векторного представлення для кожного тексту
    def get_document_vector(words, model):
        word_vectors = []
        for word in words:
            if word in model.wv:
                word_vectors.append(model.wv[word])
        
        if not word_vectors:
            return np.zeros(model.vector_size)
        
        # Усереднення векторів слів
        document_vector = np.mean(word_vectors, axis=0)
        return document_vector
    
    # Отримання векторів для кожного тексту
    vector1 = get_document_vector(words1, model)
    vector2 = get_document_vector(words2, model)
    
    # Перетворення векторів для використання в функції cosine_similarity
    vectors = np.array([vector1, vector2])
    
    # Обчислення косинусної подібності
    similarity = cosine_similarity(vectors)[0, 1]
    
    return similarity

# Приклад використання
if __name__ == "__main__":
    full3 = """
    Technical Knowledge and Experience:

    Frontend Technologies:

    Proficiency in HTML5, CSS3 (SASS/SCSS), and JavaScript/TypeScript.
    Experience with modern frameworks such as React.js, Next.js, and Vue.js.
    Strong understanding of responsive design, cross-browser compatibility, and performance optimization.
    Familiarity with state management systems (e.g., Redux/Redux Toolkit) and integrating with REST APIs/GraphQL.
    Backend and Full-Stack: (for applicable positions)

    Experience with Node.js and working with databases (both NoSQL and relational).
    Understanding of cloud services (e.g., AWS, AWS IoT Core) and IoT technologies.
    Development Tools:

    Proficiency with version control systems (e.g., Git).
    Knowledge of CI/CD processes; experience with Docker is a plus.
    Experience and Qualification Levels:

    Ranges from 2+ years of experience for Full-Stack positions to 3+ years for Frontend roles.
    Additional Requirements and Skills:

    UX/UI: Basic understanding of UX/UI principles and the ability to collaborate with designers to create intuitive and appealing interfaces.
    Problem-Solving: Strong ability to tackle complex challenges and adapt quickly to new technologies.
    Communication and Teamwork: Excellent collaboration skills, clear communication, and the capability to work in a fast-paced startup environment.
    Work Ethic: Proactive approach, attention to detail, and a commitment to investing the necessary time to achieve high-quality results.
    Language Requirements:

    Fluency in English or at least Upper-Intermediate proficiency is mandatory.
    """

    chast3 = """
    Professional Experience:
    A minimum of several years of hands-on experience in software development, with a proven track record of delivering complex projects. The candidate should have extensive experience in working on both front-end and back-end platforms, ensuring high-quality, scalable solutions.

    Technical Expertise:
    In-depth knowledge of JavaScript and TypeScript is essential. The candidate must be proficient in React for building modern, responsive user interfaces, as well as HTML, CSS, and SCSS for design and styling. Familiarity with a wide range of development tools, cutting-edge technologies, and modern tech stacks is highly valued.

    Development & Design Skills:
    The role requires the ability to design, build, and maintain robust, high-performance applications. This includes crafting responsive layouts, optimizing user experiences, and integrating innovative solutions that meet both technical and business challenges.

    Problem-Solving & Innovation:
    Demonstrated ability to tackle complex technical challenges and devise creative, efficient solutions. The candidate should be comfortable working with advanced tools and methodologies to deliver state-of-the-art products.

    Collaboration & Teamwork:
    Proven experience working effectively in agile, cross-functional teams. The candidate must be ready to collaborate with developers, designers, project managers, and other stakeholders to shape the project’s mission and drive it to success.

    Communication & Language Proficiency:
    Excellent communication skills are required, including strong fluency in English. This is necessary for understanding technical documentation, engaging in discussions with international teams, and delivering clear, concise updates.

    Full-Stack Capability (Optional):
    While the focus is on front-end development, experience with backend technologies and full-stack development is a plus. The candidate should be able to contribute to the entire software development lifecycle.

    Initiative & Responsibility:
    A proactive, self-driven attitude with a strong sense of ownership. The candidate should be prepared to take on responsibilities, from initial design and development through to deployment and ongoing maintenance, ensuring the end product meets high-performance standards.
    """

    full5 = """
    Technical Skills and Tools
    Languages & Technologies: Proficiency in JavaScript and TypeScript; solid understanding of HTML5, CSS3, and preprocessors (SCSS/SASS).
    Frameworks & Libraries: Extensive experience with React.js and Next.js is essential; familiarity with Vue.js and React Native is an asset for mobile development.
    State Management: Knowledge of Redux (or Redux Toolkit) and other state management libraries.
    API Integration: Ability to work with REST APIs (and, in some cases, GraphQL) for backend integrations.
    Version Control: Experience with Git and familiarity with Git Flow practices.
    Additional Tools: Understanding of CI/CD principles, Docker (a plus), and cloud services (such as AWS and DynamoDB) for comprehensive project development.
    Experience and Project Background
    Professional Experience: Typically around 2–3 years of experience in frontend or full-stack development; some positions may require a minimum of 1.5 years, but an average expectation is at least 2 years.
    Project Domain: Experience with IoT, mobile applications, or third-party API integrations can be advantageous, depending on the project’s focus.
    Soft Skills and Organizational Requirements
    Team Collaboration: Ability to work effectively with designers, backend developers, and other team members.
    Problem-Solving: Strong analytical skills and a creative approach to tackling technical challenges.
    Attention to Detail: Commitment to delivering clean, optimized, and responsive code.
    English Proficiency: Upper-Intermediate level or higher, as the work is conducted in English.
    Adaptability & Work Ethic: High productivity, readiness to learn new technologies, and the ability to thrive in a fast-paced startup or dynamic project environment.
    """

    chast5 = """
    Proven Experience:
    At least 3–5 years of professional experience as a software developer with a strong track record of working on end-to-end projects. Prior experience with both front-end and back-end development is essential.

    Technical Expertise:
    Solid proficiency in modern web technologies including React, TypeScript, CSS, and SCSS. You should be comfortable designing, developing, and maintaining high-performance, responsive platforms that deliver real-world solutions.

    Full-Stack Development:
    Demonstrated ability to work across the complete stack— from conceptual design and system architecture to implementation and project delivery. Familiarity with building and maintaining robust backend services is a plus.

    Collaboration and Teamwork:
    You must be ready to collaborate effectively with cross-functional teams. Experience working in agile environments, including startup settings, and contributing to innovative projects is highly valued.

    Cutting-Edge Solutions:
    A passion for working with the latest tools and technologies to create cutting-edge solutions. Experience with emerging platforms (e.g., AbyssHub) or similar environments is an advantage.

    Problem Solving and Challenges:
    The role requires you to face complex technical challenges, shape new ideas, and deliver practical solutions. Strong analytical skills and the ability to work under pressure to solve real-time problems are critical.

    English Proficiency:
    Excellent written and spoken English skills are required to effectively communicate within our global team and manage international projects.
    """

    full10 = """
    Experience & Technical Skills
    • 3+ years of experience in modern web or full-stack development using JavaScript/TypeScript.
    • Proficiency in popular frameworks and libraries—especially React.js, Next.js, and/or Vue.js.
    • Solid knowledge of HTML5, CSS3, and preprocessors like SCSS/SASS, with an understanding of responsive and adaptive design principles.
    • Experience with state management solutions (e.g., Redux or Redux Toolkit) and working with REST APIs and/or GraphQL.
    • Familiarity with backend technologies (such as Node.js, Nest.js, or similar) is often expected in full-stack roles.
    • Understanding of build tools (Webpack, Vite) and version control systems like Git, along with agile development methodologies.

    Soft Skills & Additional Requirements
    • Strong problem-solving skills and an ability to debug and optimize complex applications.
    • A keen eye for UI/UX details, ensuring a high-quality, user-friendly interface based on design mockups (e.g., Figma).
    • Excellent communication and teamwork skills, with proven experience in collaborative and remote working environments.
    • A proactive mindset with the flexibility to learn new tools and adapt quickly to a fast-paced, innovative setting.
    • High proficiency in English (typically Upper-Intermediate or higher) is mandatory.

    Nice-to-Have Attributes
    • Experience with IoT, AI integration, or blockchain/Web3 can be an advantage depending on the role.
    • Familiarity with additional tools such as Docker, CI/CD pipelines, and modern testing practices is a bonus.
    """

    chast10 = """
    Extensive Experience:
    A minimum of several years of proven experience as a developer, demonstrating a strong history of working on diverse projects across the full technology stack. A solid background in both front-end and back-end development is essential.

    Expertise in React and Frontend Technologies:
    In-depth experience with React, including Redux and modern JavaScript frameworks. You should be comfortable with TypeScript and other tools to build high-performance, responsive web applications.

    Full-Stack Development Proficiency:
    Proven knowledge of full-stack development practices—designing, developing, and maintaining end-to-end solutions. Experience with backend technologies, REST and GraphQL APIs, and building scalable platforms is a must.

    Technical Skills and Code Quality:
    Demonstrated technical ability in writing clean, efficient code. You should be familiar with using modern development tools and approaches, ensuring high-quality and maintainable applications that meet rigorous requirements.

    Collaborative Team Player:
    Strong interpersonal skills with a proven track record of working effectively in a team environment. Ability to collaborate with cross-functional teams, communicate clearly in English, and join a fast-paced work culture focused on innovation.

    Project and Product Focus:
    Experience in managing multiple projects and responsibilities simultaneously while consistently delivering robust solutions. A proactive attitude toward addressing challenges and implementing new technologies is required.

    Commitment to Excellence:
    A strong commitment to continuous improvement, staying current with cutting-edge solutions and technical trends. Ready to design and develop products that push the boundaries of modern web development.
    """
    
    similarity = cosine_similarity_word2vec(full3, chast3)
    print(f"Косинусна подібність між текстами 3 (Word2Vec): {similarity:.4f}")
    similarity = cosine_similarity_word2vec(full5, chast5)
    print(f"Косинусна подібність між текстами 5 (Word2Vec): {similarity:.4f}")
    similarity = cosine_similarity_word2vec(full10, chast10)
    print(f"Косинусна подібність між текстами 10 (Word2Vec): {similarity:.4f}")

    
       # Можна також порівняти більше текстів
    text3 = "Цей текст абсолютно не пов'язаний з попередніми."
    similarity13 = cosine_similarity_word2vec(text1, text3)
    print(f"Косинусна подібність між текстами 1 і 3 (Word2Vec): {similarity13:.4f}")

#3: 0.2230
#5: 0.1791
#10: 0.1686